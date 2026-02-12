from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from src.domain.models.user import UserRole

# Shared properties
class UserBaseSchema(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = UserRole.FIELD_OFFICER
    badge_number: Optional[str] = None
    station_id: Optional[UUID] = None
    is_active: Optional[bool] = True

# Properties to receive via API on creation
class UserCreate(UserBaseSchema):
    username: str
    email: EmailStr
    password: str
    role: UserRole

# Properties to receive via API on update
class UserUpdate(UserBaseSchema):
    password: Optional[str] = None

# Properties to return to client
class UserResponse(UserBaseSchema):
    id: UUID
    
    class Config:
        from_attributes = True
