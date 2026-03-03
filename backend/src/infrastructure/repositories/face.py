from typing import Any, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, desc
from sqlmodel import select

from src.infrastructure.repositories.base import BaseRepository
from src.domain.models.face import FaceEmbedding

class FaceRepository(BaseRepository[FaceEmbedding]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, FaceEmbedding)

    async def find_nearest_neighbors(self, query_vector: List[float], limit: int = 5) -> List[Tuple[FaceEmbedding, float]]:
        """
        Returns a list of (FaceEmbedding, distance) tuples.
        Sorts by L2 distance (Euclidean). Lower is closer.
        """
        # Using the <-> operator for L2 distance in pgvector
        statement = select(
            FaceEmbedding, 
            FaceEmbedding.embedding.l2_distance(query_vector).label("distance")
        ).order_by(
            FaceEmbedding.embedding.l2_distance(query_vector)
        ).limit(limit)

        result = await self.session.execute(statement)
        return result.all()

    async def list_by_criminal(self, criminal_id: UUID) -> List[FaceEmbedding]:
        statement = (
            select(FaceEmbedding)
            .where(FaceEmbedding.criminal_id == criminal_id)
            .order_by(desc(FaceEmbedding.is_primary), desc(FaceEmbedding.created_at))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def unset_primary_for_criminal(self, criminal_id: UUID) -> None:
        statement = (
            update(FaceEmbedding)
            .where(FaceEmbedding.criminal_id == criminal_id)
            .values(is_primary=False)
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def set_primary(self, face_id: UUID) -> None:
        statement = (
            update(FaceEmbedding)
            .where(FaceEmbedding.id == face_id)
            .values(is_primary=True)
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def get_primary_faces_for_criminals(self, criminal_ids: List[UUID]) -> List[FaceEmbedding]:
        if not criminal_ids:
            return []

        statement = (
            select(FaceEmbedding)
            .where(FaceEmbedding.criminal_id.in_(criminal_ids))
            .where(FaceEmbedding.is_primary == True)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def bulk_update_template_membership(
        self,
        updates: dict[UUID, dict[str, Any]],
    ) -> None:
        if not updates:
            return

        for face_id, values in updates.items():
            statement = (
                update(FaceEmbedding)
                .where(FaceEmbedding.id == face_id)
                .values(**values)
            )
            await self.session.execute(statement)

        await self.session.commit()

    async def get_template_eligible_face_for_promotion(
        self,
        criminal_id: UUID,
        exclude_face_id: UUID | None = None,
    ) -> FaceEmbedding | None:
        faces = await self.list_by_criminal(criminal_id)
        for face in faces:
            if exclude_face_id is not None and face.id == exclude_face_id:
                continue
            if getattr(face, "quality_status", "accepted") == "rejected":
                continue
            if bool(getattr(face, "exclude_from_template", False)):
                continue
            return face
        return None
