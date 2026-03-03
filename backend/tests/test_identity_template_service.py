from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.services.identity_template_service import IdentityTemplateService


def build_face(*, embedding, is_primary=False, created_at_offset=0):
    return SimpleNamespace(
        id=uuid4(),
        criminal_id=uuid4(),
        embedding=embedding,
        is_primary=is_primary,
        quality_status="accepted",
        embedding_version="tracenet_v1",
        created_at=datetime.now(timezone.utc) + timedelta(seconds=created_at_offset),
    )


@pytest.mark.asyncio
async def test_rebuild_for_criminal_creates_template_with_primary_and_support_roles():
    criminal_id = uuid4()
    primary_face = build_face(embedding=[1.0, 0.0, 0.0], is_primary=True, created_at_offset=0)
    support_face = build_face(embedding=[0.995, 0.05, 0.0], created_at_offset=1)
    for face in (primary_face, support_face):
        face.criminal_id = criminal_id

    face_repo = AsyncMock()
    face_repo.list_by_criminal.return_value = [primary_face, support_face]
    template_repo = AsyncMock()
    template_repo.upsert_template.side_effect = (
        lambda passed_criminal_id, payload: SimpleNamespace(criminal_id=passed_criminal_id, **payload)
    )

    service = IdentityTemplateService(template_repo, face_repo)
    template = await service.rebuild_for_criminal(criminal_id)

    face_repo.bulk_update_template_membership.assert_awaited_once()
    face_updates = face_repo.bulk_update_template_membership.await_args.args[0]
    assert face_updates[primary_face.id]["template_role"] == "primary"
    assert face_updates[support_face.id]["template_role"] == "support"
    template_repo.upsert_template.assert_awaited_once()
    assert template.primary_face_id == primary_face.id
    assert template.active_face_count == 2
    assert template.support_face_count == 1
    assert template.outlier_face_count == 0


@pytest.mark.asyncio
async def test_rebuild_for_criminal_flags_far_embedding_as_outlier():
    criminal_id = uuid4()
    primary_face = build_face(embedding=[1.0, 0.0, 0.0], is_primary=True, created_at_offset=0)
    support_face = build_face(embedding=[0.99, 0.04, 0.0], created_at_offset=1)
    outlier_face = build_face(embedding=[0.0, 1.0, 0.0], created_at_offset=2)
    for face in (primary_face, support_face, outlier_face):
        face.criminal_id = criminal_id

    face_repo = AsyncMock()
    face_repo.list_by_criminal.return_value = [primary_face, support_face, outlier_face]
    template_repo = AsyncMock()
    template_repo.upsert_template.side_effect = (
        lambda passed_criminal_id, payload: SimpleNamespace(criminal_id=passed_criminal_id, **payload)
    )

    service = IdentityTemplateService(template_repo, face_repo)
    template = await service.rebuild_for_criminal(criminal_id)

    face_updates = face_repo.bulk_update_template_membership.await_args.args[0]
    assert face_updates[primary_face.id]["template_role"] == "primary"
    assert face_updates[support_face.id]["template_role"] == "support"
    assert face_updates[outlier_face.id]["template_role"] == "outlier"
    assert template.active_face_count == 2
    assert template.outlier_face_count == 1
    assert str(outlier_face.id) in (template.outlier_face_ids or "")
