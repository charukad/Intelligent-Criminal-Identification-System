from collections import Counter
from typing import Any, Iterable
from uuid import UUID

import numpy as np

from src.core.logging import logger
from src.domain.models.face import FaceEmbedding
from src.domain.models.identity_template import IdentityTemplate
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.identity_template import IdentityTemplateRepository


TEMPLATE_VERSION = "tracenet_template_v1"
MAX_SUPPORT_FACES = 5
MIN_OUTLIER_SAMPLE = 3
OUTLIER_DISTANCE_FLOOR = 0.006
OUTLIER_MAD_BUFFER = 0.0015


class IdentityTemplateService:
    def __init__(
        self,
        template_repo: IdentityTemplateRepository,
        face_repo: FaceRepository,
    ) -> None:
        self.template_repo = template_repo
        self.face_repo = face_repo

    async def rebuild_for_criminal(self, criminal_id: UUID) -> IdentityTemplate | None:
        faces = await self.face_repo.list_by_criminal(criminal_id)
        if not faces:
            await self.template_repo.delete_by_criminal(criminal_id)
            return None

        build_result = self._build_template(faces)
        await self.face_repo.bulk_update_template_membership(build_result["face_updates"])

        template_payload = build_result.get("template_payload")
        if template_payload is None:
            await self.template_repo.delete_by_criminal(criminal_id)
            return None

        template = await self.template_repo.upsert_template(criminal_id, template_payload)
        logger.info(
            "Rebuilt identity template for criminal %s using %s active faces (%s outliers).",
            criminal_id,
            template.active_face_count,
            template.outlier_face_count,
        )
        return template

    def _build_template(self, faces: list[FaceEmbedding]) -> dict[str, Any]:
        face_updates: dict[UUID, dict[str, Any]] = {
            face.id: {
                "template_role": "archived",
                "template_distance": None,
            }
            for face in faces
        }

        eligible_faces = [
            face
            for face in faces
            if getattr(face, "embedding", None) is not None
            and getattr(face, "quality_status", "accepted") != "rejected"
        ]
        if not eligible_faces:
            return {"face_updates": face_updates, "template_payload": None}

        normalized_embeddings = {
            face.id: self._normalize_vector(np.asarray(face.embedding, dtype=np.float32))
            for face in eligible_faces
        }

        provisional_centroid = self._normalize_vector(
            np.mean(np.stack(list(normalized_embeddings.values())), axis=0)
        )
        provisional_distances = {
            face.id: self._vector_distance(normalized_embeddings[face.id], provisional_centroid)
            for face in eligible_faces
        }

        outlier_ids: set[UUID] = set()
        if len(eligible_faces) >= MIN_OUTLIER_SAMPLE:
            distance_values = np.asarray(list(provisional_distances.values()), dtype=np.float32)
            median_distance = float(np.median(distance_values))
            median_abs_deviation = float(np.median(np.abs(distance_values - median_distance)))
            outlier_threshold = max(
                OUTLIER_DISTANCE_FLOOR,
                median_distance + max((2.5 * median_abs_deviation), OUTLIER_MAD_BUFFER),
            )
            outlier_ids = {
                face.id
                for face in eligible_faces
                if provisional_distances[face.id] > outlier_threshold
            }

            if len(outlier_ids) >= len(eligible_faces):
                closest_face = min(eligible_faces, key=lambda face: provisional_distances[face.id])
                outlier_ids.discard(closest_face.id)

        inlier_faces = [face for face in eligible_faces if face.id not in outlier_ids]
        if not inlier_faces:
            closest_face = min(eligible_faces, key=lambda face: provisional_distances[face.id])
            inlier_faces = [closest_face]
            outlier_ids.discard(closest_face.id)

        inlier_centroid = self._normalize_vector(
            np.mean(np.stack([normalized_embeddings[face.id] for face in inlier_faces]), axis=0)
        )
        inlier_distances = {
            face.id: self._vector_distance(normalized_embeddings[face.id], inlier_centroid)
            for face in inlier_faces
        }

        primary_face = next((face for face in inlier_faces if getattr(face, "is_primary", False)), None)
        if primary_face is None:
            primary_face = min(inlier_faces, key=lambda face: inlier_distances[face.id])

        support_candidates = sorted(
            [face for face in inlier_faces if face.id != primary_face.id],
            key=lambda face: (inlier_distances[face.id], self._created_at_sort_value(face)),
        )
        support_faces = support_candidates[:MAX_SUPPORT_FACES]
        archived_faces = support_candidates[MAX_SUPPORT_FACES:]

        included_faces = [primary_face, *support_faces]
        template_embedding = self._normalize_vector(
            np.mean(np.stack([normalized_embeddings[face.id] for face in included_faces]), axis=0)
        )

        for face in eligible_faces:
            distance_to_template = self._vector_distance(
                normalized_embeddings[face.id],
                template_embedding,
            )
            face_updates[face.id]["template_distance"] = round(distance_to_template, 6)

            if face.id == primary_face.id:
                face_updates[face.id]["template_role"] = "primary"
            elif face.id in {candidate.id for candidate in support_faces}:
                face_updates[face.id]["template_role"] = "support"
            elif face.id in outlier_ids:
                face_updates[face.id]["template_role"] = "outlier"
            else:
                face_updates[face.id]["template_role"] = "archived"

        included_face_ids = [face.id for face in included_faces]
        support_face_ids = [face.id for face in support_faces]
        archived_face_ids = [face.id for face in archived_faces]
        outlier_face_ids = [face.id for face in eligible_faces if face.id in outlier_ids]

        template_payload = {
            "template_version": TEMPLATE_VERSION,
            "embedding_version": self._resolve_embedding_version(included_faces),
            "primary_face_id": primary_face.id,
            "included_face_ids": self._serialize_uuid_list(included_face_ids),
            "support_face_ids": self._serialize_uuid_list(support_face_ids),
            "archived_face_ids": self._serialize_uuid_list(archived_face_ids),
            "outlier_face_ids": self._serialize_uuid_list(outlier_face_ids),
            "active_face_count": len(included_face_ids),
            "support_face_count": len(support_face_ids),
            "archived_face_count": len(archived_face_ids),
            "outlier_face_count": len(outlier_face_ids),
            "template_embedding": template_embedding.astype(float).tolist(),
        }

        return {
            "face_updates": face_updates,
            "template_payload": template_payload,
        }

    def _resolve_embedding_version(self, faces: Iterable[FaceEmbedding]) -> str:
        versions = [
            getattr(face, "embedding_version", None)
            for face in faces
            if getattr(face, "embedding_version", None)
        ]
        if not versions:
            return "unknown"

        [(version, _count)] = Counter(versions).most_common(1)
        return version

    def _serialize_uuid_list(self, values: Iterable[UUID]) -> str | None:
        serialized = [str(value) for value in values]
        if not serialized:
            return None
        return "|".join(serialized)

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm <= 0:
            return vector.astype(np.float32)
        return (vector / norm).astype(np.float32)

    def _vector_distance(self, left: np.ndarray, right: np.ndarray) -> float:
        return float(np.linalg.norm(left - right))

    def _created_at_sort_value(self, face: FaceEmbedding) -> float:
        created_at = getattr(face, "created_at", None)
        if created_at is None:
            return 0.0
        return -created_at.timestamp()
