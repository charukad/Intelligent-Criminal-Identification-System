from dataclasses import dataclass
from uuid import UUID

from src.domain.models.review_case import (
    DuplicateRiskLevel,
    ReviewCase,
    ReviewCaseStatus,
    ReviewCaseType,
)
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.identity_template import IdentityTemplateRepository
from src.infrastructure.repositories.review_case import ReviewCaseRepository


DEFAULT_PROBABLE_DUPLICATE_THRESHOLD = 0.004
DEFAULT_REVIEW_THRESHOLD = 0.005


@dataclass(frozen=True)
class DuplicateIdentityAssessment:
    risk_level: DuplicateRiskLevel
    distance: float
    conflicting_criminal_id: UUID
    conflicting_criminal_name: str
    conflicting_face_id: UUID | None
    conflicting_image_url: str | None
    embedding_version: str
    template_version: str | None


class DuplicateIdentityConflictError(ValueError):
    def __init__(self, assessment: DuplicateIdentityAssessment, review_case_id: UUID):
        self.assessment = assessment
        self.review_case_id = review_case_id
        super().__init__(
            f"Possible duplicate identity conflict with {assessment.conflicting_criminal_name}"
        )


class DuplicateIdentityService:
    def __init__(
        self,
        template_repo: IdentityTemplateRepository,
        criminal_repo: CriminalRepository,
        face_repo: FaceRepository,
        review_case_repo: ReviewCaseRepository,
    ) -> None:
        self.template_repo = template_repo
        self.criminal_repo = criminal_repo
        self.face_repo = face_repo
        self.review_case_repo = review_case_repo

    async def assess_enrollment_conflict(
        self,
        criminal_id: UUID,
        embedding: list[float],
        *,
        probable_threshold: float = DEFAULT_PROBABLE_DUPLICATE_THRESHOLD,
        review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    ) -> DuplicateIdentityAssessment | None:
        template_matches = await self.template_repo.find_nearest_neighbors(embedding, limit=5)
        for template, distance in template_matches:
            if template.criminal_id == criminal_id:
                continue

            risk_level = self._classify_risk(float(distance), probable_threshold, review_threshold)
            if risk_level is None:
                return None

            criminal = await self.criminal_repo.get(template.criminal_id)
            if criminal is None:
                continue

            primary_face = None
            if getattr(template, "primary_face_id", None):
                primary_face = await self.face_repo.get(template.primary_face_id)

            return DuplicateIdentityAssessment(
                risk_level=risk_level,
                distance=round(float(distance), 6),
                conflicting_criminal_id=template.criminal_id,
                conflicting_criminal_name=f"{criminal.first_name} {criminal.last_name}",
                conflicting_face_id=getattr(primary_face, "id", None),
                conflicting_image_url=getattr(primary_face, "image_url", None),
                embedding_version=template.embedding_version,
                template_version=template.template_version,
            )

        return None

    async def create_or_update_review_case(
        self,
        *,
        source_criminal_id: UUID,
        assessment: DuplicateIdentityAssessment,
        created_by_id: UUID | None,
        source_face_id: UUID | None = None,
        submitted_filename: str | None = None,
        notes: str | None = None,
    ) -> ReviewCase:
        existing_case = await self.review_case_repo.get_open_duplicate_case(
            source_criminal_id,
            assessment.conflicting_criminal_id,
        )
        if existing_case is not None:
            existing_case.risk_level = assessment.risk_level
            existing_case.distance = assessment.distance
            existing_case.source_face_id = source_face_id
            existing_case.matched_face_id = assessment.conflicting_face_id
            existing_case.embedding_version = assessment.embedding_version
            existing_case.template_version = assessment.template_version
            existing_case.submitted_filename = submitted_filename
            existing_case.notes = notes
            self.review_case_repo.session.add(existing_case)
            await self.review_case_repo.session.commit()
            await self.review_case_repo.session.refresh(existing_case)
            return existing_case

        review_case = ReviewCase(
            case_type=ReviewCaseType.DUPLICATE_IDENTITY,
            status=ReviewCaseStatus.OPEN,
            risk_level=assessment.risk_level,
            source_criminal_id=source_criminal_id,
            matched_criminal_id=assessment.conflicting_criminal_id,
            source_face_id=source_face_id,
            matched_face_id=assessment.conflicting_face_id,
            created_by_id=created_by_id,
            distance=assessment.distance,
            embedding_version=assessment.embedding_version,
            template_version=assessment.template_version,
            submitted_filename=submitted_filename,
            notes=notes,
        )
        return await self.review_case_repo.create(review_case)

    async def resolve_review_case(
        self,
        *,
        review_case_id: UUID,
        status: ReviewCaseStatus,
        resolved_by_id: UUID | None,
        resolution_notes: str | None = None,
    ) -> ReviewCase:
        review_case = await self.review_case_repo.get(review_case_id)
        if review_case is None:
            raise ValueError("Review case not found")
        if review_case.status != ReviewCaseStatus.OPEN:
            raise ValueError("Review case is already resolved")
        if status == ReviewCaseStatus.OPEN:
            raise ValueError("Resolution status must close the review case")

        return await self.review_case_repo.resolve_case(
            review_case,
            status=status,
            resolved_by_id=resolved_by_id,
            resolution_notes=resolution_notes,
        )

    async def create_manual_review_case(
        self,
        *,
        source_criminal_id: UUID,
        matched_criminal_id: UUID,
        created_by_id: UUID | None,
        source_face_id: UUID | None = None,
        matched_face_id: UUID | None = None,
        distance: float = 0.0,
        embedding_version: str = "tracenet_v1",
        template_version: str | None = None,
        submitted_filename: str | None = None,
        notes: str | None = None,
    ) -> ReviewCase:
        if source_criminal_id == matched_criminal_id:
            raise ValueError("Source and matched criminal must be different")

        source_criminal = await self.criminal_repo.get(source_criminal_id)
        if source_criminal is None:
            raise ValueError("Source criminal not found")

        matched_criminal = await self.criminal_repo.get(matched_criminal_id)
        if matched_criminal is None:
            raise ValueError("Matched criminal not found")

        if source_face_id is not None:
            source_face = await self.face_repo.get(source_face_id)
            if source_face is None or source_face.criminal_id != source_criminal_id:
                raise ValueError("Source face record not found for the selected criminal")

        conflicting_face = None
        if matched_face_id is not None:
            conflicting_face = await self.face_repo.get(matched_face_id)
            if conflicting_face is None or conflicting_face.criminal_id != matched_criminal_id:
                raise ValueError("Matched face record not found for the selected criminal")
        else:
            primary_faces = await self.face_repo.get_primary_faces_for_criminals([matched_criminal_id])
            conflicting_face = primary_faces[0] if primary_faces else None

        assessment = DuplicateIdentityAssessment(
            risk_level=DuplicateRiskLevel.NEEDS_REVIEW,
            distance=round(float(distance), 6),
            conflicting_criminal_id=matched_criminal_id,
            conflicting_criminal_name=f"{matched_criminal.first_name} {matched_criminal.last_name}",
            conflicting_face_id=getattr(conflicting_face, "id", None),
            conflicting_image_url=getattr(conflicting_face, "image_url", None),
            embedding_version=embedding_version,
            template_version=template_version,
        )
        return await self.create_or_update_review_case(
            source_criminal_id=source_criminal_id,
            assessment=assessment,
            created_by_id=created_by_id,
            source_face_id=source_face_id,
            submitted_filename=submitted_filename,
            notes=notes,
        )

    def _classify_risk(
        self,
        distance: float,
        probable_threshold: float,
        review_threshold: float,
    ) -> DuplicateRiskLevel | None:
        if distance <= probable_threshold:
            return DuplicateRiskLevel.PROBABLE_DUPLICATE
        if distance <= review_threshold:
            return DuplicateRiskLevel.NEEDS_REVIEW
        return None
