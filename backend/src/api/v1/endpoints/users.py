from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.repositories.user import UserRepository
from src.services.user_service import UserService
from src.schemas.user import UserCreate, UserResponse, UserUpdate
from src.api.deps import get_current_active_admin
from src.domain.models.user import User

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve users. Only Admin.
    """
    repo = UserRepository(db)
    service = UserService(repo)
    return await service.get_users(skip=skip, limit=limit)

@router.post("/", response_model=UserResponse)
async def create_user(
    *,
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create new user. Only Admin.
    """
    repo = UserRepository(db)
    service = UserService(repo)
    
    # Check if exists
    user = await repo.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
        
    user_obj = User(
        username=user_in.username,
        email=user_in.email,
        role=user_in.role,
        badge_number=user_in.badge_number,
        station_id=user_in.station_id,
        hashed_password="" # Handled by service
    )
    return await service.create_user(user_obj, user_in.password)

@router.get("/{user_id}", response_model=UserResponse)
async def read_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    repo = UserRepository(db)
    service = UserService(repo)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
