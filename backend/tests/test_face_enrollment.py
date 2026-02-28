import importlib
import io
import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from src.domain.models.audit import AuditLog
from src.services import face_enrollment_service as enrollment_module
from src.services.face_enrollment_service import FaceEnrollmentService


def load_criminals_endpoint_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db",
    )

    fake_runtime = types.ModuleType("src.services.ai.runtime")
    fake_runtime.pipeline = object()
    monkeypatch.setitem(sys.modules, "src.services.ai.runtime", fake_runtime)

    fake_database = types.ModuleType("src.infrastructure.database")

    async def fake_get_db():
        yield None

    fake_database.get_db = fake_get_db
    monkeypatch.setitem(sys.modules, "src.infrastructure.database", fake_database)

    import src.api.v1.endpoints.criminals as criminals_module

    return importlib.reload(criminals_module)


@pytest.mark.asyncio
@patch("cv2.imdecode")
@patch("cv2.cvtColor")
async def test_enroll_face_success(mock_cvtColor, mock_imdecode, monkeypatch, tmp_path):
    criminal_id = uuid4()
    user_id = uuid4()
    image_bytes = b"fake-image"

    uploads_dir = tmp_path / "uploads" / "faces"
    monkeypatch.setattr(enrollment_module, "UPLOADS_DIR", uploads_dir)
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.process_image.return_value = [
        {"box": (10, 20, 40, 50), "embedding": [0.1] * 512}
    ]

    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo.create.side_effect = lambda face: face

    service = FaceEnrollmentService(pipeline, face_repo, criminal_repo, audit_repo)

    result = await service.enroll_face(
        criminal_id=criminal_id,
        image_bytes=image_bytes,
        filename="mugshot.png",
        is_primary=True,
        user_id=user_id,
    )

    face_repo.unset_primary_for_criminal.assert_awaited_once_with(criminal_id)
    face_repo.create.assert_awaited_once()
    created_face = face_repo.create.await_args.args[0]
    stored_file = uploads_dir / str(criminal_id) / f"{created_face.id}.png"

    assert stored_file.exists()
    assert stored_file.read_bytes() == image_bytes
    assert created_face.embedding_version == "tracenet_v1"
    assert created_face.is_primary is True
    assert created_face.box_x == 10
    assert created_face.box_y == 20
    assert created_face.box_w == 40
    assert created_face.box_h == 50
    assert result["created_at"] == created_face.created_at
    assert result["criminal_id"] == criminal_id
    assert result["box"] == (10, 20, 40, 50)

    audit_repo.create.assert_awaited_once()
    audit_entry = audit_repo.create.await_args.args[0]
    assert isinstance(audit_entry, AuditLog)
    assert audit_entry.action == "FACE_ENROLL"
    assert audit_entry.user_id == user_id


@pytest.mark.asyncio
@patch("cv2.imdecode")
@patch("cv2.cvtColor")
async def test_enroll_face_requires_single_detected_face(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.process_image.return_value = []

    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=uuid4())

    service = FaceEnrollmentService(pipeline, face_repo, criminal_repo, audit_repo)

    with pytest.raises(ValueError, match="No face detected"):
        await service.enroll_face(uuid4(), b"fake-image")


@pytest.mark.asyncio
async def test_enroll_criminal_face_endpoint_returns_service_result(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    expected = {
        "id": uuid4(),
        "criminal_id": criminal_id,
        "image_url": "uploads/faces/example.png",
        "is_primary": True,
        "embedding_version": "tracenet_v1",
        "created_at": datetime.now(timezone.utc),
        "box": (1, 2, 3, 4),
    }

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def enroll_face(self, **kwargs):
            assert kwargs["criminal_id"] == criminal_id
            assert kwargs["is_primary"] is True
            assert kwargs["user_id"] == current_user.id
            return expected

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())

    upload = UploadFile(
        filename="face.jpg",
        file=io.BytesIO(b"fake-image"),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    result = await criminals_module.enroll_criminal_face(
        criminal_id=criminal_id,
        file=upload,
        is_primary=True,
        current_user=current_user,
        db=AsyncMock(),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_enroll_criminal_face_endpoint_maps_validation_error(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def enroll_face(self, **_kwargs):
            raise ValueError("No face detected in the uploaded image")

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())

    upload = UploadFile(
        filename="face.jpg",
        file=io.BytesIO(b"fake-image"),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await criminals_module.enroll_criminal_face(
            criminal_id=uuid4(),
            file=upload,
            is_primary=False,
            current_user=SimpleNamespace(id=uuid4()),
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "No face detected in the uploaded image"


@pytest.mark.asyncio
async def test_list_criminal_faces_returns_enrolled_faces(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    stored_face = SimpleNamespace(
        id=uuid4(),
        criminal_id=criminal_id,
        image_url="uploads/faces/sample.jpg",
        is_primary=True,
        embedding_version="tracenet_v1",
        created_at=datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc),
        box_x=11,
        box_y=22,
        box_w=33,
        box_h=44,
    )

    criminal_repo = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo = AsyncMock()
    face_repo.list_by_criminal.return_value = [stored_face]

    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: criminal_repo)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)

    result = await criminals_module.list_criminal_faces(
        criminal_id=criminal_id,
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
    )

    assert result == [
        {
            "id": stored_face.id,
            "criminal_id": criminal_id,
            "image_url": "uploads/faces/sample.jpg",
            "is_primary": True,
            "embedding_version": "tracenet_v1",
            "created_at": datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc),
            "box": (11, 22, 33, 44),
        }
    ]


@pytest.mark.asyncio
async def test_update_criminal_passes_update_data_to_repository(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    existing_criminal = SimpleNamespace(id=criminal_id, first_name="Old")
    updated_criminal = SimpleNamespace(
        id=criminal_id,
        nic=None,
        first_name="Updated",
        last_name="Name",
        aliases=None,
        dob=None,
        gender="male",
        blood_type=None,
        last_known_address=None,
        status="wanted",
        threat_level="medium",
        physical_description=None,
    )

    repo = AsyncMock()
    repo.get.return_value = existing_criminal
    repo.update.return_value = updated_criminal
    face_repo = AsyncMock()
    face_repo.get_primary_faces_for_criminals.return_value = []

    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: repo)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)

    result = await criminals_module.update_criminal(
        criminal_id=criminal_id,
        criminal_in=criminals_module.CriminalUpdate(first_name="Updated"),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
    )

    repo.update.assert_awaited_once_with(existing_criminal, {"first_name": "Updated"})
    assert result["id"] == criminal_id
    assert result["first_name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_criminal_cleans_related_records_and_commits(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    criminal = SimpleNamespace(id=criminal_id)
    face = SimpleNamespace(image_url="uploads/faces/sample.jpg")

    repo = AsyncMock()
    repo.get.return_value = criminal
    face_repo = AsyncMock()
    face_repo.list_by_criminal.return_value = [face]
    db = AsyncMock()
    delete_image = MagicMock()

    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: repo)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)
    monkeypatch.setattr(criminals_module, "delete_stored_face_image", delete_image)

    result = await criminals_module.delete_criminal(
        criminal_id=criminal_id,
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
    )

    delete_image.assert_called_once_with("uploads/faces/sample.jpg")
    assert db.execute.await_count == 4
    db.delete.assert_awaited_once_with(criminal)
    db.commit.assert_awaited_once()
    assert result == {"status": "success", "message": "Criminal record deleted"}


@pytest.mark.asyncio
async def test_delete_face_promotes_remaining_face(monkeypatch, tmp_path):
    criminal_id = uuid4()
    user_id = uuid4()
    deleted_face_id = uuid4()
    promoted_face_id = uuid4()
    uploads_dir = tmp_path / "uploads" / "faces"
    image_path = uploads_dir / str(criminal_id)
    image_path.mkdir(parents=True, exist_ok=True)
    stored_file = image_path / f"{deleted_face_id}.jpg"
    stored_file.write_bytes(b"fake-image")

    monkeypatch.setattr(enrollment_module, "UPLOADS_DIR", uploads_dir)

    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo.get.return_value = SimpleNamespace(
        id=deleted_face_id,
        criminal_id=criminal_id,
        image_url=f"uploads/faces/{criminal_id}/{deleted_face_id}.jpg",
        is_primary=True,
    )
    face_repo.list_by_criminal.return_value = [
        SimpleNamespace(id=promoted_face_id, criminal_id=criminal_id, is_primary=False)
    ]

    service = FaceEnrollmentService(MagicMock(), face_repo, criminal_repo, audit_repo)

    result = await service.delete_face(
        criminal_id=criminal_id,
        face_id=deleted_face_id,
        user_id=user_id,
    )

    assert not stored_file.exists()
    face_repo.delete.assert_awaited_once_with(deleted_face_id)
    face_repo.set_primary.assert_awaited_once_with(promoted_face_id)
    assert result["status"] == "success"
    assert result["promoted_face_id"] == str(promoted_face_id)
    audit_entry = audit_repo.create.await_args.args[0]
    assert audit_entry.action == "FACE_DELETE"


@pytest.mark.asyncio
async def test_delete_criminal_face_endpoint_returns_service_result(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    face_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    expected = {
        "status": "success",
        "message": "Face record deleted",
        "promoted_face_id": None,
    }

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def delete_face(self, **kwargs):
            assert kwargs["criminal_id"] == criminal_id
            assert kwargs["face_id"] == face_id
            assert kwargs["user_id"] == current_user.id
            return expected

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())

    result = await criminals_module.delete_criminal_face(
        criminal_id=criminal_id,
        face_id=face_id,
        current_user=current_user,
        db=AsyncMock(),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_set_primary_face_updates_primary_and_audits():
    criminal_id = uuid4()
    user_id = uuid4()
    face_id = uuid4()

    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo.get.return_value = SimpleNamespace(
        id=face_id,
        criminal_id=criminal_id,
        is_primary=False,
    )

    service = FaceEnrollmentService(MagicMock(), face_repo, criminal_repo, audit_repo)

    result = await service.set_primary_face(
        criminal_id=criminal_id,
        face_id=face_id,
        user_id=user_id,
    )

    face_repo.unset_primary_for_criminal.assert_awaited_once_with(criminal_id)
    face_repo.set_primary.assert_awaited_once_with(face_id)
    audit_entry = audit_repo.create.await_args.args[0]
    assert audit_entry.action == "FACE_SET_PRIMARY"
    assert result["status"] == "success"
    assert result["face_id"] == str(face_id)


@pytest.mark.asyncio
async def test_set_criminal_face_as_primary_endpoint_returns_service_result(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    face_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    expected = {
        "status": "success",
        "message": "Primary face updated",
        "face_id": str(face_id),
    }

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def set_primary_face(self, **kwargs):
            assert kwargs["criminal_id"] == criminal_id
            assert kwargs["face_id"] == face_id
            assert kwargs["user_id"] == current_user.id
            return expected

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())

    result = await criminals_module.set_criminal_face_as_primary(
        criminal_id=criminal_id,
        face_id=face_id,
        current_user=current_user,
        db=AsyncMock(),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_list_criminals_includes_primary_face_thumbnail(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    criminal = SimpleNamespace(
        id=criminal_id,
        nic="123456789V",
        first_name="John",
        last_name="Doe",
        aliases="JD",
        dob=None,
        gender="male",
        blood_type="O+",
        last_known_address="Colombo",
        status="wanted",
        threat_level="high",
        physical_description="Scar on cheek",
    )
    primary_face = SimpleNamespace(
        criminal_id=criminal_id,
        image_url="uploads/faces/john.jpg",
    )

    count_result = MagicMock()
    count_result.scalar.return_value = 1
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = [criminal]
    db = AsyncMock()
    db.execute.side_effect = [count_result, data_result]

    face_repo = AsyncMock()
    face_repo.get_primary_faces_for_criminals.return_value = [primary_face]
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)

    result = await criminals_module.list_criminals(
        page=1,
        limit=10,
        q=None,
        threat_level=None,
        status=None,
        legal_status=None,
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
    )

    assert result["items"][0]["primary_face_image_url"] == "uploads/faces/john.jpg"
    assert result["items"][0]["first_name"] == "John"
