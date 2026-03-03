from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from src.domain.models.review_case import DuplicateRiskLevel, ReviewCaseStatus, ReviewCaseType


class ReviewCaseCriminalRef(BaseModel):
    id: UUID
    name: str
    primary_face_image_url: Optional[str] = None


class DuplicateReviewSummary(BaseModel):
    review_case_id: UUID
    risk_level: DuplicateRiskLevel
    distance: float
    conflicting_criminal: ReviewCaseCriminalRef
    status: ReviewCaseStatus = ReviewCaseStatus.OPEN


class ReviewCaseResponse(BaseModel):
    id: UUID
    case_type: ReviewCaseType
    status: ReviewCaseStatus
    risk_level: DuplicateRiskLevel
    source_criminal: ReviewCaseCriminalRef
    matched_criminal: ReviewCaseCriminalRef
    source_face_id: Optional[UUID] = None
    matched_face_id: Optional[UUID] = None
    distance: float
    embedding_version: str
    template_version: Optional[str] = None
    submitted_filename: Optional[str] = None
    notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_by_id: Optional[UUID] = None
    resolved_by_id: Optional[UUID] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class ReviewCaseResolveRequest(BaseModel):
    status: ReviewCaseStatus
    resolution_notes: Optional[str] = None
