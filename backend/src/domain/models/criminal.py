from typing import Optional, List
import uuid
from datetime import date
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class LegalStatus(str, Enum):
    WANTED = "wanted"
    IN_CUSTODY = "in_custody"
    RELEASED = "released"
    DECEASED = "deceased"
    CLEARED = "cleared"

class CriminalBase(SQLModel):
    nic: Optional[str] = Field(index=True, unique=True)
    first_name: str
    last_name: str
    aliases: Optional[str] = None # Comma separated
    dob: Optional[date] = None
    gender: str
    blood_type: Optional[str] = None
    last_known_address: Optional[str] = None
    
    status: LegalStatus = Field(default=LegalStatus.WANTED)
    threat_level: ThreatLevel = Field(default=ThreatLevel.LOW)
    physical_description: Optional[str] = None  # JSON or text blob

class Criminal(CriminalBase, table=True):
    __tablename__ = "criminals"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Relationships
    faces: List["FaceEmbedding"] = Relationship(back_populates="criminal")
    offenses: List["Offense"] = Relationship(back_populates="criminal")
    # suspect_cases: List["CaseSuspect"] = Relationship(back_populates="criminal")
