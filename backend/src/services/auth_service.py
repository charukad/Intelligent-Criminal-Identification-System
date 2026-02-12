from typing import Tuple
from src.core.security import verify_password, create_access_token
from src.domain.models.user import User
from src.infrastructure.repositories.user import UserRepository

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, username: str, password: str) -> User | None:
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_token_for_user(self, user: User) -> str:
        return create_access_token(subject=user.id)
