from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import Column, DateTime, Float, Text
from sqlmodel import Field, SQLModel


class ReviewCaseType(str, Enum):
    DUPLICATE_IDENTITY = "duplicate_identity"


class ReviewCaseStatus(str, Enum):
    OPEN = "open"
    CONFIRMED_DUPLICATE = "confirmed_duplicate"
    FALSE_POSITIVE = "false_positive"
    DISMISSED = "dismissed"


class DuplicateRiskLevel(str, Enum):
    PROBABLE_DUPLICATE = "probable_duplicate"
    NEEDS_REVIEW = "needs_review"


class ReviewCaseBase(SQLModel):
    case_type: ReviewCaseType = Field(default=ReviewCaseType.DUPLICATE_IDENTITY)
    status: ReviewCaseStatus = Field(default=ReviewCaseStatus.OPEN)
    risk_level: DuplicateRiskLevel
    source_criminal_id: uuid.UUID = Field(foreign_key="criminals.id", index=True)
    matched_criminal_id: uuid.UUID = Field(foreign_key="criminals.id", index=True)
    source_face_id: Optional[uuid.UUID] = Field(default=None, foreign_key="face_embeddings.id")
    matched_face_id: Optional[uuid.UUID] = Field(default=None, foreign_key="face_embeddings.id")
    created_by_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    resolved_by_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    distance: float = Field(sa_column=Column(Float, nullable=False))
    embedding_version: str = "tracenet_v1"
    template_version: Optional[str] = None
    submitted_filename: Optional[str] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    resolution_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))


class ReviewCase(ReviewCaseBase, table=True):
    __tablename__ = "review_cases"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
