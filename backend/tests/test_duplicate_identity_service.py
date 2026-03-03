from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain.models.review_case import DuplicateRiskLevel
from src.services.duplicate_identity_service import DuplicateIdentityService


@pytest.mark.asyncio
async def test_create_manual_review_case_uses_needs_review_and_primary_face_fallback():
    source_criminal_id = uuid4()
    matched_criminal_id = uuid4()
    matched_face_id = uuid4()

    template_repo = AsyncMock()
    criminal_repo = AsyncMock()
    face_repo = AsyncMock()
    review_case_repo = AsyncMock()

    criminal_repo.get.side_effect = [
        SimpleNamespace(id=source_criminal_id, first_name="Source", last_name="Person"),
        SimpleNamespace(id=matched_criminal_id, first_name="Matched", last_name="Person"),
    ]
    face_repo.get_primary_faces_for_criminals.return_value = [
        SimpleNamespace(id=matched_face_id, criminal_id=matched_criminal_id, image_url="uploads/faces/matched.png")
    ]
    review_case_repo.get_open_duplicate_case.return_value = None
    expected_case = SimpleNamespace(id=uuid4())
    review_case_repo.create.return_value = expected_case

    service = DuplicateIdentityService(template_repo, criminal_repo, face_repo, review_case_repo)
    result = await service.create_manual_review_case(
        source_criminal_id=source_criminal_id,
        matched_criminal_id=matched_criminal_id,
        created_by_id=uuid4(),
        distance=0.0049,
        embedding_version="tracenet_v1",
        template_version="tracenet_template_v1",
        notes="Manual escalation from recognition review",
    )

    assert result is expected_case
    review_case_repo.create.assert_awaited_once()
    created_case = review_case_repo.create.await_args.args[0]
    assert created_case.risk_level == DuplicateRiskLevel.NEEDS_REVIEW
    assert created_case.matched_face_id == matched_face_id
    assert created_case.distance == 0.0049


@pytest.mark.asyncio
async def test_create_manual_review_case_rejects_same_criminal_pair():
    service = DuplicateIdentityService(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())
    criminal_id = uuid4()

    with pytest.raises(ValueError, match="must be different"):
        await service.create_manual_review_case(
            source_criminal_id=criminal_id,
            matched_criminal_id=criminal_id,
            created_by_id=uuid4(),
        )
