from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.repositories.user import UserRepository
from src.services.user_service import UserService
from src.schemas.user import UserCreate, UserResponse, UserUpdate
from src.api.deps import get_current_active_admin, get_current_user, get_admin_or_senior_officer
from src.domain.models.user import User

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_or_senior_officer()),  # Admin and Senior Officer can list users
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve users list.
    Requires: Admin or Senior Officer role.
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
    current_user: User = Depends(get_current_user),  # Users can view themselves, admins can view anyone
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get user by ID.
    Users can view their own profile. Admins and Senior Officers can view any user.
    """
    repo = UserRepository(db)
    service = UserService(repo)
    
    # Check permissions
    if str(user_id) != str(current_user.id):
        # Only admin/senior can view other users
        if current_user.role not in ["admin", "senior_officer"]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view other users' profiles"
            )
    
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update user.
    Users can update their own profile (except role).
    Only Admins can update other users or change roles.
    """
    repo = UserRepository(db)
    service = UserService(repo)
    
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Self-update logic
    if str(user_id) == str(current_user.id):
        # Users can update themselves, but not their role
        if user_in.role is not None and user_in.role != current_user.role:
            raise HTTPException(
                status_code=403,
                detail="Cannot change your own role"
            )
    else:
        # Only admins can update other users
        if current_user.role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admins can update other users"
            )
    
    # Update user
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field != "password":  # Password handled separately
            setattr(user, field, value)
    
    # Update password if provided
    if user_in.password:
        updated_user = await service.update_user_password(user_id, user_in.password)
    else:
        updated_user = await repo.update(user)
    
    return updated_user

@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_admin),  # Only Admin can delete
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete user.
    Requires: Admin role.
    """
    repo = UserRepository(db)
    
    # Prevent self-deletion
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await repo.delete(user_id)
    return {"status": "success", "message": "User deleted"}
