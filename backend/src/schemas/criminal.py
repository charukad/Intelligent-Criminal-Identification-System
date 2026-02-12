from typing import Optional, List
from datetime import date
from uuid import UUID
from pydantic import BaseModel
from src.domain.models.criminal import ThreatLevel, LegalStatus

class CriminalBaseSchema(BaseModel):
    nic: Optional[str] = None
    first_name: str
    last_name: str
    aliases: Optional[str] = None
    dob: Optional[date] = None
    gender: str
    blood_type: Optional[str] = None
    last_known_address: Optional[str] = None
    status: LegalStatus = LegalStatus.WANTED
    threat_level: ThreatLevel = ThreatLevel.LOW
    physical_description: Optional[str] = None

class CriminalCreate(CriminalBaseSchema):
    pass

class CriminalUpdate(BaseModel):
    status: Optional[LegalStatus] = None
    threat_level: Optional[ThreatLevel] = None
    last_known_address: Optional[str] = None
    physical_description: Optional[str] = None

class CriminalResponse(CriminalBaseSchema):
    id: UUID
    
    class Config:
        from_attributes = True
