from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import create_access_token
from src.domain.models.user import User, UserRole
from src.infrastructure.database import get_db
from src.infrastructure.repositories.user import UserRepository

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        
        if token_data is None:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        user_id = token_data
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
        
    user_repo = UserRepository(db)
    user = await user_repo.get(UUID(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_active:
         raise HTTPException(status_code=400, detail="Inactive user")
         
    return user

async def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Admin privileges required"
        )
    return current_user

def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/")
        async def endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def check_role(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required one of: {[role.value for role in allowed_roles]}"
            )
        return current_user
    return check_role

# Convenience dependencies for common permission levels
def get_admin_or_senior_officer():
    """Allows Admin and Senior Officer roles"""
    return require_role(UserRole.ADMIN, UserRole.SENIOR_OFFICER)

def get_officer_or_above():
    """Allows Admin, Senior Officer, and Field Officer roles (excludes Viewer)"""
    return require_role(UserRole.ADMIN, UserRole.SENIOR_OFFICER, UserRole.FIELD_OFFICER)

def get_any_authenticated_user():
    """Allows any authenticated user (all roles)"""
    return get_current_user
