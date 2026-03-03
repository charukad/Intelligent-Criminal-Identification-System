from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel
from src.domain.models.criminal import ThreatLevel, LegalStatus
from src.schemas.face_quality import FaceQualityResponse
from src.schemas.identity_template import IdentityTemplateResponse
from src.schemas.review_case import DuplicateReviewSummary

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
    nic: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    aliases: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    last_known_address: Optional[str] = None
    status: Optional[LegalStatus] = None
    threat_level: Optional[ThreatLevel] = None
    physical_description: Optional[str] = None

class CriminalResponse(CriminalBaseSchema):
    id: UUID
    primary_face_image_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class CriminalListResponse(BaseModel):
    items: List[CriminalResponse]
    total: int
    page: int
    pages: int


class CriminalFaceResponse(BaseModel):
    id: UUID
    criminal_id: UUID
    image_url: str
    is_primary: bool
    embedding_version: str
    created_at: datetime
    box: tuple[int, int, int, int]
    exclude_from_template: bool = False
    operator_review_status: str = "normal"
    operator_review_notes: str | None = None
    template_role: str
    template_distance: float | None = None
    quality: FaceQualityResponse
    duplicate_review: DuplicateReviewSummary | None = None


class CriminalFaceReviewActionResponse(BaseModel):
    status: str
    message: str
    promoted_face_id: UUID | None = None
    face: CriminalFaceResponse


class CriminalTemplateRebuildResponse(BaseModel):
    status: str
    message: str
    criminal_id: UUID
    template: IdentityTemplateResponse | None = None
