from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.repositories.base import BaseRepository
from src.domain.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        statement = select(User).where(User.username == username)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
