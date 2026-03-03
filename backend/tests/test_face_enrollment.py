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
from src.domain.models.review_case import DuplicateRiskLevel, ReviewCaseStatus, ReviewCaseType
from src.services.ai.face_quality import FaceQualityReport
from src.services.duplicate_identity_service import (
    DuplicateIdentityAssessment,
    DuplicateIdentityConflictError,
)
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
    template_service = AsyncMock()
    quality_assessor = MagicMock()
    quality_assessor.assess.return_value = FaceQualityReport(
        status="accepted_with_warnings",
        quality_score=82.5,
        blur_score=95.0,
        brightness_score=162.0,
        face_area_ratio=0.2,
        warnings=["poor_lighting"],
    )
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo.create.side_effect = lambda face: face

    service = FaceEnrollmentService(
        pipeline,
        face_repo,
        criminal_repo,
        audit_repo,
        quality_assessor=quality_assessor,
        template_service=template_service,
    )

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
    assert created_face.quality_status == "accepted_with_warnings"
    assert created_face.quality_score == 82.5
    assert created_face.blur_score == 95.0
    assert created_face.brightness_score == 162.0
    assert created_face.face_area_ratio == 0.2
    assert created_face.pose_score == 100.0
    assert created_face.occlusion_score == 100.0
    assert created_face.quality_warnings == "poor_lighting"
    template_service.rebuild_for_criminal.assert_awaited_once_with(criminal_id)
    assert result["created_at"] == created_face.created_at
    assert result["criminal_id"] == criminal_id
    assert result["box"] == (10, 20, 40, 50)
    assert result["exclude_from_template"] is False
    assert result["operator_review_status"] == "normal"
    assert result["operator_review_notes"] is None
    assert result["template_role"] == "archived"
    assert result["template_distance"] is None
    assert result["quality"] == {
        "status": "accepted_with_warnings",
        "quality_score": 82.5,
        "blur_score": 95.0,
        "brightness_score": 162.0,
        "face_area_ratio": 0.2,
        "pose_score": 100.0,
        "occlusion_score": 100.0,
        "warnings": ["poor_lighting"],
    }

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
@patch("cv2.imdecode")
@patch("cv2.cvtColor")
async def test_enroll_face_rejects_low_quality_images(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.process_image.return_value = [
        {"box": (10, 20, 40, 50), "embedding": [0.1] * 512}
    ]

    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    template_service = AsyncMock()
    quality_assessor = MagicMock()
    quality_assessor.assess.return_value = FaceQualityReport(
        status="rejected",
        quality_score=12.0,
        blur_score=10.0,
        brightness_score=120.0,
        face_area_ratio=0.2,
        rejection_reasons=["face_too_blurry"],
    )
    criminal_repo.get.return_value = SimpleNamespace(id=uuid4())

    service = FaceEnrollmentService(
        pipeline,
        face_repo,
        criminal_repo,
        audit_repo,
        quality_assessor=quality_assessor,
        template_service=template_service,
    )

    with pytest.raises(ValueError, match="too blurry"):
        await service.enroll_face(uuid4(), b"fake-image")

    face_repo.create.assert_not_awaited()
    audit_repo.create.assert_not_awaited()
    template_service.rebuild_for_criminal.assert_not_awaited()


@pytest.mark.asyncio
@patch("cv2.imdecode")
@patch("cv2.cvtColor")
async def test_enroll_face_blocks_probable_duplicate_conflict(mock_cvtColor, mock_imdecode):
    criminal_id = uuid4()
    conflict_case_id = uuid4()

    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.process_image.return_value = [
        {"box": (10, 20, 40, 50), "embedding": [0.1] * 512}
    ]

    face_repo = AsyncMock()
    criminal_repo = AsyncMock()
    audit_repo = AsyncMock()
    template_service = AsyncMock()
    duplicate_service = AsyncMock()
    quality_assessor = MagicMock()
    quality_assessor.assess.return_value = FaceQualityReport(
        status="accepted",
        quality_score=90.0,
        blur_score=100.0,
        brightness_score=120.0,
        face_area_ratio=0.2,
    )
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    duplicate_service.assess_enrollment_conflict.return_value = DuplicateIdentityAssessment(
        risk_level=DuplicateRiskLevel.PROBABLE_DUPLICATE,
        distance=0.0031,
        conflicting_criminal_id=uuid4(),
        conflicting_criminal_name="Jane Doe",
        conflicting_face_id=uuid4(),
        conflicting_image_url="uploads/faces/jane.png",
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
    )
    duplicate_service.create_or_update_review_case.return_value = SimpleNamespace(
        id=conflict_case_id,
        status=ReviewCaseStatus.OPEN,
    )

    service = FaceEnrollmentService(
        pipeline,
        face_repo,
        criminal_repo,
        audit_repo,
        quality_assessor=quality_assessor,
        template_service=template_service,
        duplicate_identity_service=duplicate_service,
    )

    with pytest.raises(DuplicateIdentityConflictError) as exc_info:
        await service.enroll_face(criminal_id, b"fake-image", filename="face.png")

    assert exc_info.value.review_case_id == conflict_case_id
    face_repo.create.assert_not_awaited()
    audit_repo.create.assert_not_awaited()
    template_service.rebuild_for_criminal.assert_not_awaited()


@pytest.mark.asyncio
@patch("cv2.imdecode")
@patch("cv2.cvtColor")
async def test_enroll_face_returns_duplicate_review_for_needs_review(mock_cvtColor, mock_imdecode, monkeypatch, tmp_path):
    criminal_id = uuid4()
    user_id = uuid4()

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
    template_service = AsyncMock()
    duplicate_service = AsyncMock()
    quality_assessor = MagicMock()
    quality_assessor.assess.return_value = FaceQualityReport(
        status="accepted_with_warnings",
        quality_score=81.0,
        blur_score=95.0,
        brightness_score=150.0,
        face_area_ratio=0.2,
        warnings=["face_small_in_frame"],
    )
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo.create.side_effect = lambda face: face
    assessment = DuplicateIdentityAssessment(
        risk_level=DuplicateRiskLevel.NEEDS_REVIEW,
        distance=0.0047,
        conflicting_criminal_id=uuid4(),
        conflicting_criminal_name="Review Person",
        conflicting_face_id=uuid4(),
        conflicting_image_url="uploads/faces/review.png",
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
    )
    duplicate_service.assess_enrollment_conflict.return_value = assessment
    review_case = SimpleNamespace(id=uuid4(), status=ReviewCaseStatus.OPEN)
    duplicate_service.create_or_update_review_case.side_effect = [review_case, review_case]

    service = FaceEnrollmentService(
        pipeline,
        face_repo,
        criminal_repo,
        audit_repo,
        quality_assessor=quality_assessor,
        template_service=template_service,
        duplicate_identity_service=duplicate_service,
    )

    result = await service.enroll_face(
        criminal_id=criminal_id,
        image_bytes=b"fake-image",
        filename="review.png",
        user_id=user_id,
    )

    assert result["duplicate_review"] == {
        "review_case_id": review_case.id,
        "risk_level": DuplicateRiskLevel.NEEDS_REVIEW,
        "distance": 0.0047,
        "conflicting_criminal": {
            "id": assessment.conflicting_criminal_id,
            "name": "Review Person",
            "primary_face_image_url": "uploads/faces/review.png",
        },
        "status": ReviewCaseStatus.OPEN,
    }
    assert duplicate_service.create_or_update_review_case.await_count == 2


@pytest.mark.asyncio
async def test_mark_face_as_bad_excludes_it_and_promotes_replacement():
    criminal_id = uuid4()
    user_id = uuid4()
    face_id = uuid4()
    replacement_id = uuid4()

    face = SimpleNamespace(
        id=face_id,
        criminal_id=criminal_id,
        image_url="uploads/faces/bad.png",
        is_primary=True,
        exclude_from_template=False,
        operator_review_status="normal",
        operator_review_notes=None,
        embedding_version="tracenet_v1",
        created_at=datetime.now(timezone.utc),
        box_x=1,
        box_y=2,
        box_w=3,
        box_h=4,
        quality_status="accepted",
        quality_score=90.0,
        blur_score=90.0,
        brightness_score=130.0,
        face_area_ratio=0.2,
        pose_score=100.0,
        occlusion_score=100.0,
        quality_warnings=None,
        template_role="primary",
        template_distance=0.0012,
    )
    refreshed_face = SimpleNamespace(
        **{
            **face.__dict__,
            "is_primary": False,
            "exclude_from_template": True,
            "operator_review_status": "marked_bad",
            "operator_review_notes": "Background obstruction",
            "template_role": "archived",
            "template_distance": None,
        }
    )
    replacement_face = SimpleNamespace(id=replacement_id)

    face_repo = AsyncMock()
    face_repo.get.side_effect = [face, refreshed_face]
    face_repo.update.return_value = refreshed_face
    face_repo.get_template_eligible_face_for_promotion.return_value = replacement_face
    criminal_repo = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    audit_repo = AsyncMock()
    template_service = AsyncMock()

    service = FaceEnrollmentService(
        pipeline=MagicMock(),
        face_repo=face_repo,
        criminal_repo=criminal_repo,
        audit_repo=audit_repo,
        template_service=template_service,
    )

    result = await service.mark_face_as_bad(
        criminal_id=criminal_id,
        face_id=face_id,
        user_id=user_id,
        notes="Background obstruction",
    )

    update_payload = face_repo.update.await_args.args[1]
    assert update_payload["exclude_from_template"] is True
    assert update_payload["operator_review_status"] == "marked_bad"
    assert update_payload["operator_review_notes"] == "Background obstruction"
    assert update_payload["is_primary"] is False
    face_repo.set_primary.assert_awaited_once_with(replacement_id)
    template_service.rebuild_for_criminal.assert_awaited_once_with(criminal_id)
    assert result["promoted_face_id"] == str(replacement_id)
    assert result["face"]["exclude_from_template"] is True
    assert result["face"]["operator_review_status"] == "marked_bad"
    assert result["face"]["operator_review_notes"] == "Background obstruction"
    audit_repo.create.assert_awaited_once()


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
        "exclude_from_template": False,
        "operator_review_status": "normal",
        "operator_review_notes": None,
        "template_role": "primary",
        "template_distance": 0.0012,
        "quality": {
            "status": "accepted",
            "quality_score": 90.0,
            "blur_score": 120.0,
            "brightness_score": 130.0,
            "face_area_ratio": 0.2,
            "pose_score": 100.0,
            "occlusion_score": 100.0,
            "warnings": [],
        },
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
async def test_enroll_criminal_face_endpoint_maps_duplicate_conflict(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    review_case_id = uuid4()
    assessment = DuplicateIdentityAssessment(
        risk_level=DuplicateRiskLevel.PROBABLE_DUPLICATE,
        distance=0.0032,
        conflicting_criminal_id=uuid4(),
        conflicting_criminal_name="Existing Person",
        conflicting_face_id=uuid4(),
        conflicting_image_url="uploads/faces/existing.png",
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
    )

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def enroll_face(self, **_kwargs):
            raise DuplicateIdentityConflictError(assessment, review_case_id)

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "ReviewCaseRepository", lambda _db: object())

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

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["review_case_id"] == str(review_case_id)
    assert exc_info.value.detail["risk_level"] == "probable_duplicate"


@pytest.mark.asyncio
async def test_mark_bad_face_endpoint_returns_service_result(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    face_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    expected = {
        "status": "success",
        "message": "Face enrollment marked as bad and excluded from the active template.",
        "promoted_face_id": None,
        "face": {
            "id": face_id,
            "criminal_id": criminal_id,
            "image_url": "uploads/faces/example.png",
            "is_primary": False,
            "embedding_version": "tracenet_v1",
            "created_at": datetime.now(timezone.utc),
            "box": (1, 2, 3, 4),
            "exclude_from_template": True,
            "operator_review_status": "marked_bad",
            "operator_review_notes": "Blurred crop",
            "template_role": "archived",
            "template_distance": None,
            "quality": {
                "status": "accepted",
                "quality_score": 90.0,
                "blur_score": 120.0,
                "brightness_score": 130.0,
                "face_area_ratio": 0.2,
                "pose_score": 100.0,
                "occlusion_score": 100.0,
                "warnings": [],
            },
        },
    }

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def mark_face_as_bad(self, **kwargs):
            assert kwargs["criminal_id"] == criminal_id
            assert kwargs["face_id"] == face_id
            assert kwargs["notes"] == "Blurred crop"
            assert kwargs["user_id"] == current_user.id
            return expected

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateRepository", lambda _db: object())

    result = await criminals_module.mark_criminal_face_as_bad(
        criminal_id=criminal_id,
        face_id=face_id,
        notes="Blurred crop",
        current_user=current_user,
        db=AsyncMock(),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_recompute_template_endpoint_returns_service_result(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    criminal_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    expected = {
        "status": "success",
        "message": "Identity template rebuilt from the current enrolled faces.",
        "criminal_id": criminal_id,
        "template": {
            "id": uuid4(),
            "criminal_id": criminal_id,
            "template_version": "tracenet_template_v1",
            "embedding_version": "tracenet_v1",
            "primary_face_id": uuid4(),
            "included_face_ids": [uuid4()],
            "support_face_ids": [],
            "archived_face_ids": [],
            "outlier_face_ids": [],
            "active_face_count": 1,
            "support_face_count": 0,
            "archived_face_count": 0,
            "outlier_face_count": 0,
            "updated_at": datetime.now(timezone.utc),
        },
    }

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def recompute_template(self, **kwargs):
            assert kwargs["criminal_id"] == criminal_id
            assert kwargs["user_id"] == current_user.id
            return expected

    monkeypatch.setattr(criminals_module, "FaceEnrollmentService", FakeService)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateRepository", lambda _db: object())

    result = await criminals_module.recompute_criminal_template(
        criminal_id=criminal_id,
        current_user=current_user,
        db=AsyncMock(),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_list_duplicate_review_cases_endpoint_returns_cases(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    review_case = SimpleNamespace(
        id=uuid4(),
        case_type=ReviewCaseType.DUPLICATE_IDENTITY,
        status=ReviewCaseStatus.OPEN,
        risk_level=DuplicateRiskLevel.NEEDS_REVIEW,
        source_criminal_id=uuid4(),
        matched_criminal_id=uuid4(),
        source_face_id=None,
        matched_face_id=None,
        distance=0.0048,
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
        submitted_filename="review.png",
        notes="Auto-generated",
        resolution_notes=None,
        created_by_id=None,
        resolved_by_id=None,
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
    )

    review_case_repo = MagicMock()
    review_case_repo.list_cases = AsyncMock(return_value=[review_case])
    criminal_repo = MagicMock()
    criminal_repo.get = AsyncMock(side_effect=[
        SimpleNamespace(first_name="Source", last_name="Person"),
        SimpleNamespace(first_name="Matched", last_name="Person"),
    ])
    face_repo = MagicMock()
    face_repo.get_primary_faces_for_criminals = AsyncMock(side_effect=[
        [SimpleNamespace(image_url="uploads/faces/source.png")],
        [SimpleNamespace(image_url="uploads/faces/matched.png")],
    ])

    monkeypatch.setattr(criminals_module, "ReviewCaseRepository", lambda _db: review_case_repo)
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: criminal_repo)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)

    result = await criminals_module.list_duplicate_review_cases(
        status=ReviewCaseStatus.OPEN,
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
    )

    assert len(result) == 1
    assert result[0]["source_criminal"]["name"] == "Source Person"
    assert result[0]["matched_criminal"]["primary_face_image_url"] == "uploads/faces/matched.png"


@pytest.mark.asyncio
async def test_create_manual_duplicate_review_case_endpoint_returns_case(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    review_case = SimpleNamespace(
        id=uuid4(),
        case_type=ReviewCaseType.DUPLICATE_IDENTITY,
        status=ReviewCaseStatus.OPEN,
        risk_level=DuplicateRiskLevel.NEEDS_REVIEW,
        source_criminal_id=uuid4(),
        matched_criminal_id=uuid4(),
        source_face_id=uuid4(),
        matched_face_id=uuid4(),
        distance=0.0048,
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
        submitted_filename="identify-upload.png",
        notes="Manual escalation from recognition review",
        resolution_notes=None,
        created_by_id=uuid4(),
        resolved_by_id=None,
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
    )

    class FakeDuplicateService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def create_manual_review_case(self, **kwargs):
            assert kwargs["source_criminal_id"] == review_case.source_criminal_id
            assert kwargs["matched_criminal_id"] == review_case.matched_criminal_id
            assert kwargs["distance"] == 0.0048
            return review_case

    criminal_repo = MagicMock()
    criminal_repo.get = AsyncMock(side_effect=[
        SimpleNamespace(first_name="Source", last_name="Person"),
        SimpleNamespace(first_name="Matched", last_name="Person"),
    ])
    face_repo = MagicMock()
    face_repo.get_primary_faces_for_criminals = AsyncMock(side_effect=[
        [SimpleNamespace(image_url="uploads/faces/source.png")],
        [SimpleNamespace(image_url="uploads/faces/matched.png")],
    ])

    monkeypatch.setattr(criminals_module, "DuplicateIdentityService", FakeDuplicateService)
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: criminal_repo)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)
    monkeypatch.setattr(criminals_module, "ReviewCaseRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateRepository", lambda _db: object())

    payload = criminals_module.ManualDuplicateReviewCaseCreateRequest(
        source_criminal_id=review_case.source_criminal_id,
        matched_criminal_id=review_case.matched_criminal_id,
        source_face_id=review_case.source_face_id,
        matched_face_id=review_case.matched_face_id,
        distance=0.0048,
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
        submitted_filename="identify-upload.png",
        notes="Manual escalation from recognition review",
    )

    result = await criminals_module.create_manual_duplicate_review_case(
        review_case_in=payload,
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
    )

    assert result["id"] == review_case.id
    assert result["source_criminal"]["name"] == "Source Person"
    assert result["matched_criminal"]["name"] == "Matched Person"


@pytest.mark.asyncio
async def test_resolve_duplicate_review_case_endpoint_returns_resolved_case(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    review_case = SimpleNamespace(
        id=uuid4(),
        case_type=ReviewCaseType.DUPLICATE_IDENTITY,
        status=ReviewCaseStatus.CONFIRMED_DUPLICATE,
        risk_level=DuplicateRiskLevel.PROBABLE_DUPLICATE,
        source_criminal_id=uuid4(),
        matched_criminal_id=uuid4(),
        source_face_id=None,
        matched_face_id=None,
        distance=0.0031,
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
        submitted_filename="dup.png",
        notes="Auto-generated",
        resolution_notes="Confirmed by operator",
        created_by_id=None,
        resolved_by_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        resolved_at=datetime.now(timezone.utc),
    )

    class FakeDuplicateService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def resolve_review_case(self, **kwargs):
            assert kwargs["status"] == ReviewCaseStatus.CONFIRMED_DUPLICATE
            return review_case

    criminal_repo = MagicMock()
    criminal_repo.get = AsyncMock(side_effect=[
        SimpleNamespace(first_name="Source", last_name="Person"),
        SimpleNamespace(first_name="Matched", last_name="Person"),
    ])
    face_repo = MagicMock()
    face_repo.get_primary_faces_for_criminals = AsyncMock(side_effect=[[], []])

    monkeypatch.setattr(criminals_module, "DuplicateIdentityService", FakeDuplicateService)
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: criminal_repo)
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: face_repo)
    monkeypatch.setattr(criminals_module, "ReviewCaseRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateRepository", lambda _db: object())

    result = await criminals_module.resolve_duplicate_review_case(
        review_case_id=review_case.id,
        resolution_in=SimpleNamespace(
            status=ReviewCaseStatus.CONFIRMED_DUPLICATE,
            resolution_notes="Confirmed by operator",
        ),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
    )

    assert result["status"] == ReviewCaseStatus.CONFIRMED_DUPLICATE
    assert result["matched_criminal"]["name"] == "Matched Person"


@pytest.mark.asyncio
async def test_merge_duplicate_review_case_endpoint_returns_merge_summary(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    review_case_id = uuid4()
    survivor_criminal_id = uuid4()

    class FakeMergeService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def merge_from_review_case(self, **kwargs):
            assert kwargs["review_case_id"] == review_case_id
            assert kwargs["survivor_criminal_id"] == survivor_criminal_id
            return {
                "status": "success",
                "review_case_id": str(review_case_id),
                "survivor_criminal_id": str(survivor_criminal_id),
                "merged_criminal_id": str(uuid4()),
                "moved_face_count": 3,
                "moved_offense_count": 1,
                "moved_alert_count": 2,
                "moved_audit_count": 4,
                "dismissed_review_case_count": 1,
                "survivor_name": "Survivor Profile",
            }

    monkeypatch.setattr(criminals_module, "CriminalMergeService", FakeMergeService)
    monkeypatch.setattr(criminals_module, "CriminalRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "FaceRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "ReviewCaseRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "AuditRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateRepository", lambda _db: object())
    monkeypatch.setattr(criminals_module, "IdentityTemplateService", lambda *_args, **_kwargs: object())

    result = await criminals_module.merge_duplicate_review_case(
        review_case_id=review_case_id,
        merge_in=SimpleNamespace(
            survivor_criminal_id=survivor_criminal_id,
            resolution_notes="Merge confirmed",
        ),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
    )

    assert result["status"] == "success"
    assert result["survivor_criminal_id"] == str(survivor_criminal_id)


@pytest.mark.asyncio
async def test_preview_face_quality_endpoint_returns_service_result(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)
    expected = {
        "status": "accepted_with_warnings",
        "detected_face_count": 1,
        "decision_reason": "accepted_with_warnings",
        "message": "Image can be enrolled, but quality warnings should be reviewed.",
        "box": (1, 2, 3, 4),
        "quality": {
            "status": "accepted_with_warnings",
            "quality_score": 81.0,
            "blur_score": 96.0,
            "brightness_score": 172.0,
            "face_area_ratio": 0.2,
            "pose_score": 100.0,
            "occlusion_score": 100.0,
            "warnings": ["poor_lighting"],
        },
    }

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        def preview_image(self, image_bytes):
            assert image_bytes == b"fake-image"
            return expected

    monkeypatch.setattr(criminals_module, "FaceQualityService", FakeService)

    upload = UploadFile(
        filename="face.jpg",
        file=io.BytesIO(b"fake-image"),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    result = await criminals_module.preview_face_quality(
        file=upload,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_preview_face_quality_endpoint_maps_validation_error(monkeypatch):
    criminals_module = load_criminals_endpoint_module(monkeypatch)

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

        def preview_image(self, _image_bytes):
            raise ValueError("Invalid image data")

    monkeypatch.setattr(criminals_module, "FaceQualityService", FakeService)

    upload = UploadFile(
        filename="face.jpg",
        file=io.BytesIO(b"fake-image"),
        headers=Headers({"content-type": "image/jpeg"}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await criminals_module.preview_face_quality(
            file=upload,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid image data"


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
        template_role="support",
        template_distance=0.0026,
        quality_status="accepted_with_warnings",
        quality_score=83.5,
        blur_score=91.0,
        brightness_score=175.0,
        face_area_ratio=0.143,
        pose_score=78.0,
        occlusion_score=84.0,
        quality_warnings="poor_lighting|face_small_in_frame",
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
            "exclude_from_template": False,
            "operator_review_status": "normal",
            "operator_review_notes": None,
            "template_role": "support",
            "template_distance": 0.0026,
            "quality": {
                "status": "accepted_with_warnings",
                "quality_score": 83.5,
                "blur_score": 91.0,
                "brightness_score": 175.0,
                "face_area_ratio": 0.143,
                "pose_score": 78.0,
                "occlusion_score": 84.0,
                "warnings": ["poor_lighting", "face_small_in_frame"],
            },
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
    assert db.execute.await_count == 6
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
    template_service = AsyncMock()
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

    service = FaceEnrollmentService(
        MagicMock(),
        face_repo,
        criminal_repo,
        audit_repo,
        template_service=template_service,
    )

    result = await service.delete_face(
        criminal_id=criminal_id,
        face_id=deleted_face_id,
        user_id=user_id,
    )

    assert not stored_file.exists()
    face_repo.delete.assert_awaited_once_with(deleted_face_id)
    face_repo.set_primary.assert_awaited_once_with(promoted_face_id)
    template_service.rebuild_for_criminal.assert_awaited_once_with(criminal_id)
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
    template_service = AsyncMock()
    criminal_repo.get.return_value = SimpleNamespace(id=criminal_id)
    face_repo.get.return_value = SimpleNamespace(
        id=face_id,
        criminal_id=criminal_id,
        is_primary=False,
    )

    service = FaceEnrollmentService(
        MagicMock(),
        face_repo,
        criminal_repo,
        audit_repo,
        template_service=template_service,
    )

    result = await service.set_primary_face(
        criminal_id=criminal_id,
        face_id=face_id,
        user_id=user_id,
    )

    face_repo.unset_primary_for_criminal.assert_awaited_once_with(criminal_id)
    face_repo.set_primary.assert_awaited_once_with(face_id)
    template_service.rebuild_for_criminal.assert_awaited_once_with(criminal_id)
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
