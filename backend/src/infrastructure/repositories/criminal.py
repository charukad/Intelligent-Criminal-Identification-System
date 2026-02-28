from typing import Optional, List
from sqlmodel import select, col
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.base import BaseRepository
from src.domain.models.criminal import Criminal

class CriminalRepository(BaseRepository[Criminal]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Criminal)

    async def get_by_nic(self, nic: str) -> Optional[Criminal]:
        statement = select(Criminal).where(Criminal.nic == nic)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def search_by_name_or_nic(self, query: str) -> List[Criminal]:
        # Case insensitive partial match on first name, last name, or NIC
        statement = select(Criminal).where(
            (col(Criminal.first_name).ilike(f"%{query}%")) |
            (col(Criminal.last_name).ilike(f"%{query}%")) |
            (col(Criminal.nic).ilike(f"%{query}%"))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()
