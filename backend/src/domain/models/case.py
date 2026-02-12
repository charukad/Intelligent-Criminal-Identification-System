from typing import Optional, List
import uuid
from datetime import datetime, date
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

# Forward refs
# from src.domain.models.criminal import Criminal
# from src.domain.models.station import Station
# from src.domain.models.user import User

class CaseStatus(str, Enum):
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    CLOSED = "closed"
    COLD = "cold"
    SUSPENDED = "suspended"

class CaseBase(SQLModel):
    case_number: str = Field(unique=True, index=True)
    title: str
    description: Optional[str] = None
    status: CaseStatus = Field(default=CaseStatus.OPEN)
    date_opened: datetime = Field(default_factory=datetime.utcnow)
    station_id: Optional[uuid.UUID] = Field(default=None, foreign_key="stations.id")
    lead_officer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

class Case(CaseBase, table=True):
    __tablename__ = "cases"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Relationships
    station: Optional["Station"] = Relationship(back_populates="cases")
    lead_officer: Optional["User"] = Relationship(back_populates="cases_assigned")
    offenses: List["Offense"] = Relationship(back_populates="case")

class OffenseBase(SQLModel):
    offense_type: str  # Robbery, Homicide etc.
    description: Optional[str] = None
    date_committed: Optional[date] = None
    verdict: Optional[str] = None
    sentence: Optional[str] = None

class Offense(OffenseBase, table=True):
    __tablename__ = "offenses"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    case_id: uuid.UUID = Field(foreign_key="cases.id")
    criminal_id: uuid.UUID = Field(foreign_key="criminals.id")
    
    # Relationships
    case: Optional[Case] = Relationship(back_populates="offenses")
    criminal: Optional["Criminal"] = Relationship(back_populates="offenses")
