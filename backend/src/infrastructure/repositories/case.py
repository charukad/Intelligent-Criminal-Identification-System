from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.base import BaseRepository
from src.domain.models.case import Case

class CaseRepository(BaseRepository[Case]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Case)

    async def get_by_case_number(self, case_number: str) -> Optional[Case]:
        statement = select(Case).where(Case.case_number == case_number)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
