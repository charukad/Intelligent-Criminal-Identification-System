from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import numpy as np
import pytest

from src.services.embedding_migration_service import EmbeddingMigrationService


def build_face(*, embedding_version: str = "tracenet_v1"):
    return SimpleNamespace(
        id=uuid4(),
        criminal_id=uuid4(),
        image_url="uploads/faces/example.jpg",
        embedding_version=embedding_version,
        embedding_model_name="TraceNet v1",
        embedding_migrated_at=None,
        embedding=[0.1, 0.2, 0.3],
        template_role="support",
        template_distance=0.01,
        box_x=10,
        box_y=20,
        box_w=50,
        box_h=60,
        created_at=datetime.now(timezone.utc),
    )


def build_service():
    session = SimpleNamespace(add=MagicMock(), commit=AsyncMock(), execute=AsyncMock())
    face_repo = SimpleNamespace(session=session, get=AsyncMock())
    template_repo = SimpleNamespace(
        upsert_template=AsyncMock(),
        delete_by_criminal=AsyncMock(),
    )
    template_service = SimpleNamespace(rebuild_for_criminal=AsyncMock())
    service = EmbeddingMigrationService(
        face_repo=face_repo,
        template_repo=template_repo,
        template_service=template_service,
    )
    return service, face_repo, template_repo, template_service, session


@pytest.mark.asyncio
async def test_reembed_all_faces_dry_run_returns_plan_without_writes(tmp_path: Path):
    service, _face_repo, _template_repo, _template_service, session = build_service()
    service.build_plan = AsyncMock(return_value={"eligible_face_count": 2, "items": []})
    service.export_snapshot = AsyncMock()

    result = await service.reembed_all_faces(
        target_embedding_version="facenet_vggface2",
        backup_path=tmp_path / "snapshot.json",
        dry_run=True,
    )

    assert result["status"] == "dry_run"
    service.export_snapshot.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reembed_all_faces_updates_face_metadata_and_rebuilds_templates(monkeypatch):
    service, _face_repo, _template_repo, template_service, session = build_service()
    face = build_face()
    service.build_plan = AsyncMock(return_value={"eligible_face_count": 1, "items": []})
    service._load_faces = AsyncMock(return_value=[face])
    service._build_skip_reason = MagicMock(return_value=None)
    service._load_rgb_image = MagicMock(return_value=np.zeros((64, 64, 3), dtype=np.uint8))
    service._extract_face_region = MagicMock(return_value={"crop": np.zeros((32, 32, 3), dtype=np.uint8)})

    fake_pipeline = SimpleNamespace(embedder=SimpleNamespace(embed_face=MagicMock(return_value=[0.9, 0.1, 0.0])))
    monkeypatch.setattr("src.services.embedding_migration_service._load_pipeline", lambda *_args, **_kwargs: fake_pipeline)

    result = await service.reembed_all_faces(target_embedding_version="facenet_vggface2")

    assert result["status"] == "completed"
    assert result["updated_face_count"] == 1
    assert face.embedding_version == "facenet_vggface2"
    assert face.embedding_model_name == "FaceNet VGGFace2"
    assert face.embedding == [0.9, 0.1, 0.0]
    session.commit.assert_awaited()
    template_service.rebuild_for_criminal.assert_awaited_once_with(face.criminal_id)


@pytest.mark.asyncio
async def test_restore_snapshot_restores_face_and_template_state(tmp_path: Path):
    service, face_repo, template_repo, _template_service, session = build_service()
    face = build_face(embedding_version="facenet_vggface2")
    face_repo.get.return_value = face

    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "source_embedding_version": "tracenet_v1",
                "target_embedding_version": "facenet_vggface2",
                "faces": [
                    {
                        "id": str(face.id),
                        "criminal_id": str(face.criminal_id),
                        "image_url": face.image_url,
                        "embedding_version": "tracenet_v1",
                        "embedding_model_name": "TraceNet v1",
                        "embedding_migrated_at": None,
                        "template_role": "primary",
                        "template_distance": 0.002,
                        "embedding": [0.2, 0.3, 0.4],
                    }
                ],
                "templates": [
                    {
                        "criminal_id": str(face.criminal_id),
                        "template_version": "tracenet_template_v1",
                        "embedding_version": "tracenet_v1",
                        "primary_face_id": str(face.id),
                        "included_face_ids": str(face.id),
                        "support_face_ids": None,
                        "archived_face_ids": None,
                        "outlier_face_ids": None,
                        "active_face_count": 1,
                        "support_face_count": 0,
                        "archived_face_count": 0,
                        "outlier_face_count": 0,
                        "template_embedding": [0.2, 0.3, 0.4],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = await service.restore_snapshot(snapshot_path)

    assert result["status"] == "restored"
    assert result["restored_face_count"] == 1
    assert face.embedding_version == "tracenet_v1"
    assert face.embedding_model_name == "TraceNet v1"
    assert face.template_role == "primary"
    assert face.embedding == [0.2, 0.3, 0.4]
    session.commit.assert_awaited()
    template_repo.upsert_template.assert_awaited_once()
