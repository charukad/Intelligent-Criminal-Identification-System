import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import cv2
import numpy as np
from sqlmodel import select

from src.domain.models.face import FaceEmbedding
from src.domain.models.identity_template import IdentityTemplate
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.identity_template import IdentityTemplateRepository
from src.services.ai.strategies import get_model_version_metadata, normalize_embedding_version
from src.services.identity_template_service import IdentityTemplateService


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _load_pipeline(target_embedding_version: str, model_path: Path | None):
    from src.services.ai.runtime import get_pipeline

    return get_pipeline(target_embedding_version, model_path=model_path)


class EmbeddingMigrationService:
    def __init__(
        self,
        *,
        face_repo: FaceRepository,
        template_repo: IdentityTemplateRepository,
        template_service: IdentityTemplateService,
        file_root: Path | None = None,
    ) -> None:
        self.face_repo = face_repo
        self.template_repo = template_repo
        self.template_service = template_service
        self.session = face_repo.session
        self.file_root = file_root or BACKEND_ROOT

    async def build_plan(
        self,
        *,
        target_embedding_version: str,
        source_embedding_version: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        resolved_target = normalize_embedding_version(target_embedding_version)
        faces = await self._load_faces(
            source_embedding_version=source_embedding_version,
            limit=limit,
        )

        plan_items: list[dict[str, Any]] = []
        eligible_count = 0
        skipped_count = 0
        for face in faces:
            skip_reason = self._build_skip_reason(face, resolved_target)
            if skip_reason is None:
                eligible_count += 1
            else:
                skipped_count += 1

            plan_items.append(
                {
                    "face_id": str(face.id),
                    "criminal_id": str(face.criminal_id),
                    "image_url": face.image_url,
                    "current_embedding_version": face.embedding_version,
                    "target_embedding_version": resolved_target,
                    "skip_reason": skip_reason,
                }
            )

        return {
            "target_embedding_version": resolved_target,
            "source_embedding_version": normalize_embedding_version(source_embedding_version)
            if source_embedding_version
            else None,
            "face_count": len(faces),
            "eligible_face_count": eligible_count,
            "skipped_face_count": skipped_count,
            "items": plan_items,
        }

    async def export_snapshot(
        self,
        snapshot_path: Path,
        *,
        target_embedding_version: str,
        source_embedding_version: str | None = None,
        limit: int | None = None,
        reason: str = "pre_migration_backup",
    ) -> dict[str, Any]:
        faces = await self._load_faces(
            source_embedding_version=source_embedding_version,
            limit=limit,
        )
        criminal_ids = sorted({face.criminal_id for face in faces}, key=str)
        templates = await self._load_templates(criminal_ids)

        snapshot = {
            "snapshot_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "source_embedding_version": normalize_embedding_version(source_embedding_version)
            if source_embedding_version
            else None,
            "target_embedding_version": normalize_embedding_version(target_embedding_version),
            "faces": [self._serialize_face(face) for face in faces],
            "templates": [self._serialize_template(template) for template in templates],
        }
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return {
            "snapshot_path": str(snapshot_path),
            "face_count": len(faces),
            "template_count": len(templates),
        }

    async def reembed_all_faces(
        self,
        *,
        target_embedding_version: str,
        source_embedding_version: str | None = None,
        model_path: Path | None = None,
        backup_path: Path | None = None,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        resolved_target = normalize_embedding_version(target_embedding_version)
        plan = await self.build_plan(
            target_embedding_version=resolved_target,
            source_embedding_version=source_embedding_version,
            limit=limit,
        )

        if dry_run:
            return {
                "status": "dry_run",
                "plan": plan,
                "backup_path": str(backup_path) if backup_path else None,
            }

        if backup_path is not None:
            await self.export_snapshot(
                backup_path,
                target_embedding_version=resolved_target,
                source_embedding_version=source_embedding_version,
                limit=limit,
            )

        pipeline = _load_pipeline(resolved_target, model_path)
        metadata = get_model_version_metadata(resolved_target)
        faces = await self._load_faces(
            source_embedding_version=source_embedding_version,
            limit=limit,
        )
        updated_faces = 0
        failed_faces: list[dict[str, Any]] = []
        touched_criminal_ids: set[UUID] = set()
        migrated_at = datetime.now(timezone.utc)

        for face in faces:
            skip_reason = self._build_skip_reason(face, resolved_target)
            if skip_reason is not None:
                continue

            try:
                image = self._load_rgb_image(self._resolve_image_path(face.image_url))
                face_region = self._extract_face_region(face, image, pipeline)
                embedding = pipeline.embedder.embed_face(face_region["crop"])
            except Exception as exc:
                failed_faces.append(
                    {
                        "face_id": str(face.id),
                        "criminal_id": str(face.criminal_id),
                        "image_url": face.image_url,
                        "reason": str(exc),
                    }
                )
                continue

            face.embedding = embedding
            face.embedding_version = resolved_target
            face.embedding_model_name = metadata["display_name"]
            face.embedding_migrated_at = migrated_at
            self.session.add(face)
            updated_faces += 1
            touched_criminal_ids.add(face.criminal_id)

        await self.session.commit()

        rebuilt_templates = 0
        for criminal_id in sorted(touched_criminal_ids, key=str):
            await self.template_service.rebuild_for_criminal(criminal_id)
            rebuilt_templates += 1

        return {
            "status": "completed",
            "target_embedding_version": resolved_target,
            "updated_face_count": updated_faces,
            "failed_face_count": len(failed_faces),
            "rebuilt_template_count": rebuilt_templates,
            "failed_faces": failed_faces,
            "backup_path": str(backup_path) if backup_path else None,
            "active_runtime_version_hint": resolved_target,
        }

    async def restore_snapshot(
        self,
        snapshot_path: Path,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        face_items = snapshot.get("faces", [])
        template_items = snapshot.get("templates", [])

        if dry_run:
            return {
                "status": "dry_run",
                "snapshot_path": str(snapshot_path),
                "face_count": len(face_items),
                "template_count": len(template_items),
                "target_embedding_version": snapshot.get("target_embedding_version"),
            }

        restored_faces = 0
        missing_face_ids: list[str] = []
        touched_criminal_ids: set[UUID] = set()
        for face_item in face_items:
            face = await self.face_repo.get(UUID(face_item["id"]))
            if face is None:
                missing_face_ids.append(face_item["id"])
                continue

            face.embedding = face_item["embedding"]
            face.embedding_version = face_item["embedding_version"]
            face.embedding_model_name = face_item.get("embedding_model_name") or face.embedding_model_name
            face.embedding_migrated_at = self._parse_datetime(face_item.get("embedding_migrated_at"))
            face.template_role = face_item.get("template_role") or "archived"
            face.template_distance = face_item.get("template_distance")
            self.session.add(face)
            restored_faces += 1
            touched_criminal_ids.add(face.criminal_id)

        await self.session.commit()

        restored_templates = 0
        snapshot_templates_by_criminal = {
            UUID(template_item["criminal_id"]): template_item
            for template_item in template_items
        }
        for criminal_id in sorted(touched_criminal_ids, key=str):
            template_item = snapshot_templates_by_criminal.get(criminal_id)
            if template_item is None:
                await self.template_repo.delete_by_criminal(criminal_id)
                continue

            payload = {
                "template_version": template_item["template_version"],
                "embedding_version": template_item["embedding_version"],
                "primary_face_id": UUID(template_item["primary_face_id"])
                if template_item.get("primary_face_id")
                else None,
                "included_face_ids": template_item.get("included_face_ids"),
                "support_face_ids": template_item.get("support_face_ids"),
                "archived_face_ids": template_item.get("archived_face_ids"),
                "outlier_face_ids": template_item.get("outlier_face_ids"),
                "active_face_count": template_item["active_face_count"],
                "support_face_count": template_item["support_face_count"],
                "archived_face_count": template_item["archived_face_count"],
                "outlier_face_count": template_item["outlier_face_count"],
                "template_embedding": template_item["template_embedding"],
            }
            await self.template_repo.upsert_template(criminal_id, payload)
            restored_templates += 1

        return {
            "status": "restored",
            "snapshot_path": str(snapshot_path),
            "restored_face_count": restored_faces,
            "missing_face_count": len(missing_face_ids),
            "missing_face_ids": missing_face_ids,
            "restored_template_count": restored_templates,
            "active_runtime_version_hint": snapshot.get("source_embedding_version"),
        }

    async def _load_faces(
        self,
        *,
        source_embedding_version: str | None = None,
        limit: int | None = None,
    ) -> list[FaceEmbedding]:
        statement = select(FaceEmbedding).order_by(FaceEmbedding.created_at, FaceEmbedding.id)
        if source_embedding_version:
            statement = statement.where(
                FaceEmbedding.embedding_version == normalize_embedding_version(source_embedding_version)
            )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def _load_templates(self, criminal_ids: list[UUID]) -> list[IdentityTemplate]:
        if not criminal_ids:
            return []
        statement = (
            select(IdentityTemplate)
            .where(IdentityTemplate.criminal_id.in_(criminal_ids))
            .order_by(IdentityTemplate.criminal_id)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    def _build_skip_reason(self, face: FaceEmbedding, target_embedding_version: str) -> str | None:
        if normalize_embedding_version(face.embedding_version) == target_embedding_version:
            return "already_target_version"
        image_path = self._resolve_image_path(face.image_url)
        if not image_path.exists():
            return "missing_image_file"
        return None

    def _resolve_image_path(self, image_url: str) -> Path:
        return self.file_root / image_url

    def _load_rgb_image(self, image_path: Path) -> np.ndarray:
        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            raise ValueError(f"Unable to decode image: {image_path}")
        return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    def _extract_face_region(
        self,
        face: FaceEmbedding,
        image: np.ndarray,
        pipeline: Any,
    ) -> dict[str, Any]:
        regions = pipeline.extract_face_regions(image)
        if len(regions) == 1:
            return regions[0]

        stored_box = self._stored_box(face)
        if stored_box is not None and regions:
            best_region = max(
                regions,
                key=lambda region: self._intersection_over_union(stored_box, region["box"]),
            )
            if self._intersection_over_union(stored_box, best_region["box"]) > 0:
                return best_region

        if stored_box is not None:
            crop = self._crop_box(image, stored_box)
            if crop.size == 0:
                raise ValueError("stored_box_crop_empty")
            return {
                "box": stored_box,
                "crop": crop,
            }

        if not regions:
            raise ValueError("no_face_detected_for_reembed")
        raise ValueError(f"ambiguous_face_detection:{len(regions)}")

    def _stored_box(self, face: FaceEmbedding) -> tuple[int, int, int, int] | None:
        if None in (face.box_x, face.box_y, face.box_w, face.box_h):
            return None
        return int(face.box_x), int(face.box_y), int(face.box_w), int(face.box_h)

    def _crop_box(self, image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = box
        height, width, _channels = image.shape
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(width, x + w), min(height, y + h)
        return image[y1:y2, x1:x2]

    def _intersection_over_union(
        self,
        left: tuple[int, int, int, int],
        right: tuple[int, int, int, int],
    ) -> float:
        lx1, ly1, lw, lh = left
        rx1, ry1, rw, rh = right
        lx2, ly2 = lx1 + lw, ly1 + lh
        rx2, ry2 = rx1 + rw, ry1 + rh

        inter_x1 = max(lx1, rx1)
        inter_y1 = max(ly1, ry1)
        inter_x2 = min(lx2, rx2)
        inter_y2 = min(ly2, ry2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        if inter_area == 0:
            return 0.0

        left_area = lw * lh
        right_area = rw * rh
        return float(inter_area / max(left_area + right_area - inter_area, 1))

    def _serialize_face(self, face: FaceEmbedding) -> dict[str, Any]:
        return {
            "id": str(face.id),
            "criminal_id": str(face.criminal_id),
            "image_url": face.image_url,
            "embedding_version": face.embedding_version,
            "embedding_model_name": getattr(face, "embedding_model_name", None),
            "embedding_migrated_at": face.embedding_migrated_at.isoformat()
            if getattr(face, "embedding_migrated_at", None)
            else None,
            "template_role": getattr(face, "template_role", None),
            "template_distance": getattr(face, "template_distance", None),
            "embedding": [float(value) for value in face.embedding],
        }

    def _serialize_template(self, template: IdentityTemplate) -> dict[str, Any]:
        return {
            "id": str(template.id),
            "criminal_id": str(template.criminal_id),
            "template_version": template.template_version,
            "embedding_version": template.embedding_version,
            "primary_face_id": str(template.primary_face_id) if template.primary_face_id else None,
            "included_face_ids": template.included_face_ids,
            "support_face_ids": template.support_face_ids,
            "archived_face_ids": template.archived_face_ids,
            "outlier_face_ids": template.outlier_face_ids,
            "active_face_count": template.active_face_count,
            "support_face_count": template.support_face_count,
            "archived_face_count": template.archived_face_count,
            "outlier_face_count": template.outlier_face_count,
            "template_embedding": [float(value) for value in template.template_embedding],
        }

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
