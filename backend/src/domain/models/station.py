from typing import Optional, List
import uuid
from sqlmodel import SQLModel, Field, Relationship

class StationBase(SQLModel):
    name: str = Field(index=True)
    district: str
    province: str
    contact_number: Optional[str] = None

class Station(StationBase, table=True):
    __tablename__ = "stations"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="station")
    cases: List["Case"] = Relationship(back_populates="station")
