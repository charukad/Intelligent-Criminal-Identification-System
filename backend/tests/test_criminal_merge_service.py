from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain.models.criminal import LegalStatus, ThreatLevel
from src.domain.models.review_case import ReviewCaseStatus
from src.services.criminal_merge_service import CriminalMergeService


@pytest.mark.asyncio
async def test_merge_from_review_case_reassigns_records_and_rebuilds_template():
    review_case_id = uuid4()
    survivor_id = uuid4()
    duplicate_id = uuid4()
    user_id = uuid4()

    session = AsyncMock()
    session.add = MagicMock()
    criminal_repo = AsyncMock()
    criminal_repo.session = session
    face_repo = AsyncMock()
    review_case_repo = AsyncMock()
    audit_repo = AsyncMock()
    template_service = AsyncMock()

    review_case = SimpleNamespace(
        id=review_case_id,
        status=ReviewCaseStatus.OPEN,
        source_criminal_id=survivor_id,
        matched_criminal_id=duplicate_id,
        resolution_notes=None,
        resolved_by_id=None,
        resolved_at=None,
    )
    other_review_case = SimpleNamespace(
        id=uuid4(),
        status=ReviewCaseStatus.OPEN,
        source_criminal_id=duplicate_id,
        matched_criminal_id=survivor_id,
        resolution_notes=None,
        resolved_by_id=None,
        resolved_at=None,
    )
    survivor = SimpleNamespace(
        id=survivor_id,
        first_name="Survivor",
        last_name="Profile",
        aliases="Alpha",
        nic=None,
        dob=None,
        blood_type=None,
        last_known_address=None,
        physical_description=None,
        threat_level=ThreatLevel.LOW,
        status=LegalStatus.WANTED,
    )
    duplicate = SimpleNamespace(
        id=duplicate_id,
        first_name="Duplicate",
        last_name="Profile",
        aliases="Beta, Alpha",
        nic="123456789V",
        dob=None,
        blood_type="O+",
        last_known_address="Colombo",
        physical_description="Scar",
        threat_level=ThreatLevel.HIGH,
        status=LegalStatus.IN_CUSTODY,
    )

    criminal_repo.get.side_effect = [survivor, duplicate]
    face_repo.list_by_criminal.side_effect = [
        [SimpleNamespace(id=uuid4(), is_primary=True), SimpleNamespace(id=uuid4(), is_primary=False)],
        [],
    ]
    review_case_repo.get.return_value = review_case
    review_case_repo.list_cases.return_value = [review_case, other_review_case]

    update_result = SimpleNamespace(rowcount=2)
    session.execute.side_effect = [
        update_result,
        update_result,
        update_result,
        update_result,
        update_result,
        update_result,
    ]

    service = CriminalMergeService(
        criminal_repo=criminal_repo,
        face_repo=face_repo,
        review_case_repo=review_case_repo,
        audit_repo=audit_repo,
        template_service=template_service,
    )

    result = await service.merge_from_review_case(
        review_case_id=review_case_id,
        survivor_criminal_id=survivor_id,
        resolved_by_id=user_id,
        resolution_notes="Confirmed duplicate",
    )

    assert result["status"] == "success"
    assert result["review_case_id"] == str(review_case_id)
    assert result["survivor_criminal_id"] == str(survivor_id)
    assert result["merged_criminal_id"] == str(duplicate_id)
    assert result["moved_face_count"] == 2
    assert result["moved_offense_count"] == 2
    assert result["moved_alert_count"] == 2
    assert result["moved_audit_count"] == 2
    assert survivor.aliases == "Alpha, Beta"
    assert survivor.nic == "123456789V"
    assert survivor.blood_type == "O+"
    assert survivor.last_known_address == "Colombo"
    assert survivor.physical_description == "Scar"
    assert survivor.threat_level == ThreatLevel.HIGH
    assert survivor.status == LegalStatus.IN_CUSTODY
    assert review_case.status == ReviewCaseStatus.CONFIRMED_DUPLICATE
    assert other_review_case.status == ReviewCaseStatus.DISMISSED
    session.delete.assert_awaited_once_with(duplicate)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(survivor)
    template_service.rebuild_for_criminal.assert_awaited_once_with(survivor_id)
    audit_repo.create.assert_awaited_once()
from unittest.mock import MagicMock
