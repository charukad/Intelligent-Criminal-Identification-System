from pathlib import Path
from typing import Any, Dict
from uuid import UUID, uuid4

import cv2
import numpy as np

from src.core.logging import logger
from src.domain.models.audit import AuditLog
from src.domain.models.face import FaceEmbedding
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.face import FaceRepository
from src.services.ai.face_quality import FaceQualityAssessor, FaceQualityReport
from src.services.ai.pipeline import FaceProcessingPipeline
from src.services.duplicate_identity_service import (
    DuplicateIdentityConflictError,
    DuplicateIdentityService,
)
from src.services.face_quality_service import get_quality_reason_message, serialize_quality_report
from src.services.identity_template_service import IdentityTemplateService
from src.schemas.identity_template import IdentityTemplateResponse


UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads" / "faces"
EMBEDDING_VERSION = "tracenet_v1"


def delete_stored_face_image(image_url: str) -> None:
    file_path = UPLOADS_DIR.parent.parent / image_url
    if file_path.exists():
        file_path.unlink()
        parent_dir = file_path.parent
        if parent_dir.exists() and not any(parent_dir.iterdir()):
            parent_dir.rmdir()


class FaceEnrollmentService:
    def __init__(
        self,
        pipeline: FaceProcessingPipeline,
        face_repo: FaceRepository,
        criminal_repo: CriminalRepository,
        audit_repo: AuditRepository,
        quality_assessor: FaceQualityAssessor | None = None,
        template_service: IdentityTemplateService | None = None,
        duplicate_identity_service: DuplicateIdentityService | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.face_repo = face_repo
        self.criminal_repo = criminal_repo
        self.audit_repo = audit_repo
        self.quality_assessor = quality_assessor or FaceQualityAssessor()
        self.template_service = template_service
        self.duplicate_identity_service = duplicate_identity_service

    async def enroll_face(
        self,
        criminal_id: UUID,
        image_bytes: bytes,
        filename: str | None = None,
        is_primary: bool = False,
        user_id: UUID | None = None,
    ) -> Dict[str, Any]:
        criminal = await self.criminal_repo.get(criminal_id)
        if not criminal:
            raise ValueError("Criminal not found")

        image = self._decode_image(image_bytes)
        processed_faces = self.pipeline.process_image(image)

        if not processed_faces:
            raise ValueError("No face detected in the uploaded image")
        if len(processed_faces) > 1:
            raise ValueError("Please upload an image containing exactly one face")

        face_data = processed_faces[0]
        x, y, w, h = (int(value) for value in face_data["box"])
        quality_report = self.quality_assessor.assess(
            image,
            (x, y, w, h),
            landmarks=face_data.get("landmarks"),
        )
        if quality_report.should_reject:
            raise ValueError(self._format_quality_rejection(quality_report))

        duplicate_review = None
        if self.duplicate_identity_service is not None:
            duplicate_assessment = await self.duplicate_identity_service.assess_enrollment_conflict(
                criminal_id,
                face_data["embedding"],
            )
            if duplicate_assessment is not None:
                review_case = await self.duplicate_identity_service.create_or_update_review_case(
                    source_criminal_id=criminal_id,
                    assessment=duplicate_assessment,
                    created_by_id=user_id,
                    submitted_filename=filename,
                    notes="Auto-generated during face enrollment duplicate screening.",
                )
                if duplicate_assessment.risk_level.value == "probable_duplicate":
                    raise DuplicateIdentityConflictError(duplicate_assessment, review_case.id)
                duplicate_review = self._serialize_duplicate_review(review_case, duplicate_assessment)

        face_id = uuid4()
        image_url = self._store_image(criminal_id, face_id, image_bytes, filename)

        if is_primary:
            await self.face_repo.unset_primary_for_criminal(criminal_id)

        face_embedding = FaceEmbedding(
            id=face_id,
            criminal_id=criminal_id,
            image_url=image_url,
            is_primary=is_primary,
            embedding_version=EMBEDDING_VERSION,
            box_x=x,
            box_y=y,
            box_w=w,
            box_h=h,
            quality_status=quality_report.status,
            quality_score=quality_report.quality_score,
            blur_score=quality_report.blur_score,
            brightness_score=quality_report.brightness_score,
            face_area_ratio=quality_report.face_area_ratio,
            pose_score=quality_report.pose_score,
            occlusion_score=quality_report.occlusion_score,
            quality_warnings=self._serialize_quality_warnings(quality_report.warnings),
            embedding=face_data["embedding"],
        )
        created_face = await self.face_repo.create(face_embedding)
        if duplicate_review is not None and self.duplicate_identity_service is not None:
            review_case = await self.duplicate_identity_service.create_or_update_review_case(
                source_criminal_id=criminal_id,
                assessment=duplicate_assessment,
                created_by_id=user_id,
                source_face_id=created_face.id,
                submitted_filename=filename,
                notes="Enrollment accepted with duplicate review warning.",
            )
            duplicate_review = self._serialize_duplicate_review(review_case, duplicate_assessment)
        if self.template_service is not None:
            await self.template_service.rebuild_for_criminal(criminal_id)
            refreshed_face = await self.face_repo.get(created_face.id)
            if refreshed_face is not None and getattr(refreshed_face, "id", None) == created_face.id:
                created_face = refreshed_face

        await self.audit_repo.create(
            AuditLog(
                action="FACE_ENROLL",
                details=f"Enrolled face for criminal {criminal_id}",
                user_id=user_id,
                criminal_id=criminal_id,
            )
        )
        logger.info("Enrolled face %s for criminal %s", created_face.id, criminal_id)

        return {
            "id": created_face.id,
            "criminal_id": created_face.criminal_id,
            "image_url": created_face.image_url,
            "is_primary": created_face.is_primary,
            "embedding_version": created_face.embedding_version,
            "created_at": created_face.created_at,
            "box": face_data["box"],
            "exclude_from_template": bool(getattr(created_face, "exclude_from_template", False)),
            "operator_review_status": getattr(created_face, "operator_review_status", "normal"),
            "operator_review_notes": getattr(created_face, "operator_review_notes", None),
            "template_role": getattr(created_face, "template_role", "archived"),
            "template_distance": float(created_face.template_distance) if getattr(created_face, "template_distance", None) is not None else None,
            "quality": serialize_quality_report(quality_report),
            "duplicate_review": duplicate_review,
        }

    async def delete_face(
        self,
        criminal_id: UUID,
        face_id: UUID,
        user_id: UUID | None = None,
    ) -> Dict[str, Any]:
        criminal = await self.criminal_repo.get(criminal_id)
        if not criminal:
            raise ValueError("Criminal not found")

        face = await self.face_repo.get(face_id)
        if not face or face.criminal_id != criminal_id:
            raise ValueError("Face record not found")

        was_primary = bool(face.is_primary)
        self._delete_stored_image(face.image_url)
        await self.face_repo.delete(face_id)

        promoted_face_id = None
        if was_primary:
            remaining_faces = await self.face_repo.list_by_criminal(criminal_id)
            if remaining_faces:
                promoted_face_id = remaining_faces[0].id
                await self.face_repo.set_primary(promoted_face_id)

        if self.template_service is not None:
            await self.template_service.rebuild_for_criminal(criminal_id)

        await self.audit_repo.create(
            AuditLog(
                action="FACE_DELETE",
                details=f"Deleted face {face_id} for criminal {criminal_id}",
                user_id=user_id,
                criminal_id=criminal_id,
            )
        )
        logger.info("Deleted face %s for criminal %s", face_id, criminal_id)

        return {
            "status": "success",
            "message": "Face record deleted",
            "promoted_face_id": str(promoted_face_id) if promoted_face_id else None,
        }

    async def set_primary_face(
        self,
        criminal_id: UUID,
        face_id: UUID,
        user_id: UUID | None = None,
    ) -> Dict[str, Any]:
        criminal = await self.criminal_repo.get(criminal_id)
        if not criminal:
            raise ValueError("Criminal not found")

        face = await self.face_repo.get(face_id)
        if not face or face.criminal_id != criminal_id:
            raise ValueError("Face record not found")
        if bool(getattr(face, "exclude_from_template", False)):
            raise ValueError("Cannot promote a face that has been marked as bad enrollment")

        if face.is_primary:
            return {
                "status": "success",
                "message": "Face record is already primary",
                "face_id": str(face_id),
            }

        await self.face_repo.unset_primary_for_criminal(criminal_id)
        await self.face_repo.set_primary(face_id)
        if self.template_service is not None:
            await self.template_service.rebuild_for_criminal(criminal_id)

        await self.audit_repo.create(
            AuditLog(
                action="FACE_SET_PRIMARY",
                details=f"Marked face {face_id} as primary for criminal {criminal_id}",
                user_id=user_id,
                criminal_id=criminal_id,
            )
        )
        logger.info("Set face %s as primary for criminal %s", face_id, criminal_id)

        return {
            "status": "success",
            "message": "Primary face updated",
            "face_id": str(face_id),
        }

    async def mark_face_as_bad(
        self,
        criminal_id: UUID,
        face_id: UUID,
        user_id: UUID | None = None,
        notes: str | None = None,
    ) -> Dict[str, Any]:
        criminal = await self.criminal_repo.get(criminal_id)
        if not criminal:
            raise ValueError("Criminal not found")

        face = await self.face_repo.get(face_id)
        if not face or face.criminal_id != criminal_id:
            raise ValueError("Face record not found")

        was_primary = bool(face.is_primary)
        updated_face = await self.face_repo.update(
            face,
            {
                "exclude_from_template": True,
                "operator_review_status": "marked_bad",
                "operator_review_notes": notes,
                "is_primary": False if was_primary else face.is_primary,
            },
        )

        promoted_face_id = None
        if was_primary:
            replacement_face = await self.face_repo.get_template_eligible_face_for_promotion(
                criminal_id,
                exclude_face_id=face_id,
            )
            if replacement_face is not None:
                await self.face_repo.set_primary(replacement_face.id)
                promoted_face_id = replacement_face.id

        if self.template_service is not None:
            await self.template_service.rebuild_for_criminal(criminal_id)
            refreshed_face = await self.face_repo.get(face_id)
            if refreshed_face is not None:
                updated_face = refreshed_face

        await self.audit_repo.create(
            AuditLog(
                action="FACE_MARK_BAD",
                details=f"Marked face {face_id} as bad enrollment for criminal {criminal_id}",
                user_id=user_id,
                criminal_id=criminal_id,
            )
        )
        logger.info("Marked face %s as bad enrollment for criminal %s", face_id, criminal_id)

        return {
            "status": "success",
            "message": "Face enrollment marked as bad and excluded from the active template.",
            "promoted_face_id": str(promoted_face_id) if promoted_face_id else None,
            "face": self._serialize_face_record(updated_face),
        }

    async def recompute_template(
        self,
        criminal_id: UUID,
        user_id: UUID | None = None,
    ) -> Dict[str, Any]:
        criminal = await self.criminal_repo.get(criminal_id)
        if not criminal:
            raise ValueError("Criminal not found")
        if self.template_service is None:
            raise ValueError("Identity template service is not configured")

        template = await self.template_service.rebuild_for_criminal(criminal_id)

        await self.audit_repo.create(
            AuditLog(
                action="FACE_TEMPLATE_RECOMPUTE",
                details=f"Recomputed identity template for criminal {criminal_id}",
                user_id=user_id,
                criminal_id=criminal_id,
            )
        )
        logger.info("Recomputed identity template for criminal %s", criminal_id)

        return {
            "status": "success",
            "message": "Identity template rebuilt from the current enrolled faces.",
            "criminal_id": criminal_id,
            "template": self._serialize_template_response(template),
        }

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_np is None:
            raise ValueError("Invalid image data")
        return cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)

    def _store_image(
        self,
        criminal_id: UUID,
        face_id: UUID,
        image_bytes: bytes,
        filename: str | None,
    ) -> str:
        suffix = Path(filename or "").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            suffix = ".jpg"

        face_dir = UPLOADS_DIR / str(criminal_id)
        face_dir.mkdir(parents=True, exist_ok=True)
        file_path = face_dir / f"{face_id}{suffix}"
        file_path.write_bytes(image_bytes)
        return str(file_path.relative_to(UPLOADS_DIR.parent.parent))

    def _delete_stored_image(self, image_url: str) -> None:
        delete_stored_face_image(image_url)

    def _format_quality_rejection(self, quality_report: FaceQualityReport) -> str:
        reason = quality_report.primary_rejection_reason or "unknown_quality_issue"
        return get_quality_reason_message(reason)

    def _serialize_quality_warnings(self, warnings: list[str]) -> str | None:
        if not warnings:
            return None
        return "|".join(warnings)

    def _serialize_duplicate_review(self, review_case: Any, assessment: Any) -> dict[str, Any]:
        return {
            "review_case_id": review_case.id,
            "risk_level": assessment.risk_level,
            "distance": float(assessment.distance),
            "conflicting_criminal": {
                "id": assessment.conflicting_criminal_id,
                "name": assessment.conflicting_criminal_name,
                "primary_face_image_url": assessment.conflicting_image_url,
            },
            "status": getattr(review_case, "status", "open"),
        }

    def _serialize_face_record(self, face: FaceEmbedding) -> dict[str, Any]:
        return {
            "id": face.id,
            "criminal_id": face.criminal_id,
            "image_url": face.image_url,
            "is_primary": face.is_primary,
            "embedding_version": face.embedding_version,
            "created_at": face.created_at,
            "box": (
                face.box_x if face.box_x is not None else 0,
                face.box_y if face.box_y is not None else 0,
                face.box_w if face.box_w is not None else 0,
                face.box_h if face.box_h is not None else 0,
            ),
            "exclude_from_template": bool(getattr(face, "exclude_from_template", False)),
            "operator_review_status": getattr(face, "operator_review_status", "normal"),
            "operator_review_notes": getattr(face, "operator_review_notes", None),
            "template_role": getattr(face, "template_role", "archived"),
            "template_distance": float(face.template_distance) if getattr(face, "template_distance", None) is not None else None,
            "quality": {
                "status": face.quality_status or "accepted",
                "quality_score": float(face.quality_score or 0.0),
                "blur_score": float(face.blur_score or 0.0),
                "brightness_score": float(face.brightness_score or 0.0),
                "face_area_ratio": float(face.face_area_ratio or 0.0),
                "pose_score": float(face.pose_score or 0.0),
                "occlusion_score": float(face.occlusion_score or 0.0),
                "warnings": (face.quality_warnings.split("|") if face.quality_warnings else []),
            },
            "duplicate_review": None,
        }

    def _deserialize_uuid_list(self, serialized_values: str | None) -> list[UUID]:
        if not serialized_values:
            return []
        return [UUID(value) for value in serialized_values.split("|") if value]

    def _serialize_template_response(self, template: Any) -> IdentityTemplateResponse | None:
        if template is None:
            return None
        return IdentityTemplateResponse(
            id=template.id,
            criminal_id=template.criminal_id,
            template_version=template.template_version,
            embedding_version=template.embedding_version,
            primary_face_id=template.primary_face_id,
            included_face_ids=self._deserialize_uuid_list(template.included_face_ids),
            support_face_ids=self._deserialize_uuid_list(template.support_face_ids),
            archived_face_ids=self._deserialize_uuid_list(template.archived_face_ids),
            outlier_face_ids=self._deserialize_uuid_list(template.outlier_face_ids),
            active_face_count=template.active_face_count,
            support_face_count=template.support_face_count,
            archived_face_count=template.archived_face_count,
            outlier_face_count=template.outlier_face_count,
            updated_at=template.updated_at,
        )
