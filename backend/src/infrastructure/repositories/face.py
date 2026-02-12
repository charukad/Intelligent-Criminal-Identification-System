from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pgvector.sqlalchemy import Vector

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
