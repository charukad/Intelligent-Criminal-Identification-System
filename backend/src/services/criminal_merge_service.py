from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update

from src.domain.models.alert import Alert
from src.domain.models.audit import AuditLog
from src.domain.models.case import Offense
from src.domain.models.criminal import Criminal, LegalStatus, ThreatLevel
from src.domain.models.face import FaceEmbedding
from src.domain.models.identity_template import IdentityTemplate
from src.domain.models.review_case import ReviewCase, ReviewCaseStatus
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.review_case import ReviewCaseRepository
from src.services.identity_template_service import IdentityTemplateService


THREAT_LEVEL_RANK = {
    ThreatLevel.LOW: 0,
    ThreatLevel.MEDIUM: 1,
    ThreatLevel.HIGH: 2,
    ThreatLevel.CRITICAL: 3,
}

STATUS_RANK = {
    LegalStatus.CLEARED: 0,
    LegalStatus.RELEASED: 1,
    LegalStatus.WANTED: 2,
    LegalStatus.IN_CUSTODY: 3,
    LegalStatus.DECEASED: 4,
}


class CriminalMergeService:
    def __init__(
        self,
        criminal_repo: CriminalRepository,
        face_repo: FaceRepository,
        review_case_repo: ReviewCaseRepository,
        audit_repo: AuditRepository,
        template_service: IdentityTemplateService | None = None,
    ) -> None:
        self.criminal_repo = criminal_repo
        self.face_repo = face_repo
        self.review_case_repo = review_case_repo
        self.audit_repo = audit_repo
        self.template_service = template_service
        self.session = criminal_repo.session

    async def merge_from_review_case(
        self,
        *,
        review_case_id: UUID,
        survivor_criminal_id: UUID,
        resolved_by_id: UUID | None,
        resolution_notes: str | None = None,
    ) -> dict[str, Any]:
        review_case = await self.review_case_repo.get(review_case_id)
        if review_case is None:
            raise ValueError("Review case not found")
        if review_case.status != ReviewCaseStatus.OPEN:
            raise ValueError("Review case is already resolved")
        if survivor_criminal_id not in {review_case.source_criminal_id, review_case.matched_criminal_id}:
            raise ValueError("Survivor criminal must be one of the review-case criminals")

        duplicate_criminal_id = (
            review_case.matched_criminal_id
            if survivor_criminal_id == review_case.source_criminal_id
            else review_case.source_criminal_id
        )

        survivor = await self.criminal_repo.get(survivor_criminal_id)
        duplicate = await self.criminal_repo.get(duplicate_criminal_id)
        if survivor is None or duplicate is None:
            raise ValueError("One or more criminal records no longer exist")

        duplicate_faces = await self.face_repo.list_by_criminal(duplicate_criminal_id)
        survivor_faces = await self.face_repo.list_by_criminal(survivor_criminal_id)
        survivor_has_primary = any(face.is_primary for face in survivor_faces)
        duplicate_primary_face_id = next((face.id for face in duplicate_faces if face.is_primary), None)

        profile_updates = self._build_profile_updates(survivor, duplicate)
        for field, value in profile_updates.items():
            setattr(survivor, field, value)
        self.session.add(survivor)

        moved_face_ids = [face.id for face in duplicate_faces]
        if moved_face_ids:
            face_update_values: dict[str, Any] = {"criminal_id": survivor_criminal_id}
            if survivor_has_primary:
                face_update_values["is_primary"] = False
            await self.session.execute(
                sa_update(FaceEmbedding)
                .where(FaceEmbedding.id.in_(moved_face_ids))
                .values(**face_update_values)
            )

        if not survivor_has_primary and duplicate_primary_face_id is None and moved_face_ids:
            duplicate_primary_face_id = moved_face_ids[0]

        if duplicate_primary_face_id is not None:
            await self.session.execute(
                sa_update(FaceEmbedding)
                .where(FaceEmbedding.id == duplicate_primary_face_id)
                .values(is_primary=True)
            )

        moved_offense_count = await self._reassign_criminal_reference(Offense, duplicate_criminal_id, survivor_criminal_id)
        moved_alert_count = await self._reassign_criminal_reference(Alert, duplicate_criminal_id, survivor_criminal_id)
        moved_audit_count = await self._reassign_criminal_reference(AuditLog, duplicate_criminal_id, survivor_criminal_id)

        review_case_updates = await self._reassign_review_cases(
            review_case_id=review_case_id,
            survivor_criminal_id=survivor_criminal_id,
            duplicate_criminal_id=duplicate_criminal_id,
            resolved_by_id=resolved_by_id,
            resolution_notes=resolution_notes,
        )

        await self.session.execute(
            sa_delete(IdentityTemplate).where(IdentityTemplate.criminal_id == duplicate_criminal_id)
        )
        await self.session.delete(duplicate)
        await self.session.commit()
        await self.session.refresh(survivor)

        if self.template_service is not None:
            await self.template_service.rebuild_for_criminal(survivor_criminal_id)

        await self.audit_repo.create(
            AuditLog(
                action="CRIMINAL_MERGE",
                details=(
                    f"Merged criminal {duplicate_criminal_id} into {survivor_criminal_id} "
                    f"via review case {review_case_id}"
                ),
                user_id=resolved_by_id,
                criminal_id=survivor_criminal_id,
            )
        )

        return {
            "status": "success",
            "review_case_id": str(review_case_id),
            "survivor_criminal_id": str(survivor_criminal_id),
            "merged_criminal_id": str(duplicate_criminal_id),
            "moved_face_count": len(moved_face_ids),
            "moved_offense_count": moved_offense_count,
            "moved_alert_count": moved_alert_count,
            "moved_audit_count": moved_audit_count,
            "dismissed_review_case_count": review_case_updates["dismissed_review_case_count"],
            "survivor_name": f"{survivor.first_name} {survivor.last_name}",
        }

    async def _reassign_criminal_reference(
        self,
        model: Any,
        from_criminal_id: UUID,
        to_criminal_id: UUID,
    ) -> int:
        result = await self.session.execute(
            sa_update(model)
            .where(model.criminal_id == from_criminal_id)
            .values(criminal_id=to_criminal_id)
        )
        return int(result.rowcount or 0)

    async def _reassign_review_cases(
        self,
        *,
        review_case_id: UUID,
        survivor_criminal_id: UUID,
        duplicate_criminal_id: UUID,
        resolved_by_id: UUID | None,
        resolution_notes: str | None,
    ) -> dict[str, int]:
        timestamp = datetime.now(timezone.utc)

        review_cases = await self.review_case_repo.list_cases(limit=500)
        dismissed_review_case_count = 0
        for review_case in review_cases:
            touched = False
            if review_case.source_criminal_id == duplicate_criminal_id:
                review_case.source_criminal_id = survivor_criminal_id
                touched = True
            if review_case.matched_criminal_id == duplicate_criminal_id:
                review_case.matched_criminal_id = survivor_criminal_id
                touched = True

            if review_case.id == review_case_id:
                review_case.status = ReviewCaseStatus.CONFIRMED_DUPLICATE
                review_case.resolution_notes = resolution_notes or "Confirmed duplicate and merged."
                review_case.resolved_by_id = resolved_by_id
                review_case.resolved_at = timestamp
                touched = True
            else:
                if touched and review_case.source_criminal_id == review_case.matched_criminal_id:
                    review_case.status = ReviewCaseStatus.DISMISSED
                    review_case.resolution_notes = "Automatically dismissed after criminal merge."
                    review_case.resolved_by_id = resolved_by_id
                    review_case.resolved_at = timestamp
                    dismissed_review_case_count += 1

            if touched:
                self.session.add(review_case)

        return {"dismissed_review_case_count": dismissed_review_case_count}

    def _build_profile_updates(
        self,
        survivor: Criminal,
        duplicate: Criminal,
    ) -> dict[str, Any]:
        merged_aliases = self._merge_aliases(survivor.aliases, duplicate.aliases)
        return {
            "aliases": merged_aliases,
            "nic": survivor.nic or duplicate.nic,
            "dob": survivor.dob or duplicate.dob,
            "blood_type": survivor.blood_type or duplicate.blood_type,
            "last_known_address": survivor.last_known_address or duplicate.last_known_address,
            "physical_description": survivor.physical_description or duplicate.physical_description,
            "threat_level": self._pick_higher_threat_level(survivor.threat_level, duplicate.threat_level),
            "status": self._pick_higher_status(survivor.status, duplicate.status),
        }

    def _merge_aliases(self, survivor_aliases: str | None, duplicate_aliases: str | None) -> str | None:
        values: list[str] = []
        for raw_value in (survivor_aliases, duplicate_aliases):
            if not raw_value:
                continue
            values.extend([item.strip() for item in raw_value.split(",") if item.strip()])

        if not values:
            return None

        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            normalized = value.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(value)
        return ", ".join(ordered)

    def _pick_higher_threat_level(self, left: ThreatLevel, right: ThreatLevel) -> ThreatLevel:
        return left if THREAT_LEVEL_RANK[left] >= THREAT_LEVEL_RANK[right] else right

    def _pick_higher_status(self, left: LegalStatus, right: LegalStatus) -> LegalStatus:
        return left if STATUS_RANK[left] >= STATUS_RANK[right] else right
