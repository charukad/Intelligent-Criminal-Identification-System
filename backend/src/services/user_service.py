from uuid import UUID
from typing import List, Optional

from src.domain.models.user import User
from src.core.security import get_password_hash
from src.infrastructure.repositories.user import UserRepository
from src.domain.models.user import UserRole

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_user(self, user_in: User, password: str) -> User:
        user_in.hashed_password = get_password_hash(password)
        return await self.user_repo.create(user_in)

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return await self.user_repo.get_all(skip, limit)
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repo.get(user_id)
