from typing import Optional, List
import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

# Avoid circular imports by using string forward references
# from src.domain.models.station import Station

class UserRole(str, Enum):
    ADMIN = "admin"
    SENIOR_OFFICER = "senior_officer"
    FIELD_OFFICER = "field_officer"
    VIEWER = "viewer"

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    role: UserRole = Field(default=UserRole.FIELD_OFFICER)
    badge_number: Optional[str] = None
    is_active: bool = True
    station_id: Optional[uuid.UUID] = Field(default=None, foreign_key="stations.id")

class User(UserBase, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    station: Optional["Station"] = Relationship(back_populates="users")
    cases_assigned: List["Case"] = Relationship(back_populates="lead_officer")
