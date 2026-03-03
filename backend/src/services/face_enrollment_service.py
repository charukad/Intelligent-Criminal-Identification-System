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
from src.services.face_quality_service import get_quality_reason_message, serialize_quality_report
from src.services.identity_template_service import IdentityTemplateService


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
    ) -> None:
        self.pipeline = pipeline
        self.face_repo = face_repo
        self.criminal_repo = criminal_repo
        self.audit_repo = audit_repo
        self.quality_assessor = quality_assessor or FaceQualityAssessor()
        self.template_service = template_service

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
            "template_role": getattr(created_face, "template_role", "archived"),
            "template_distance": float(created_face.template_distance) if getattr(created_face, "template_distance", None) is not None else None,
            "quality": serialize_quality_report(quality_report),
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
