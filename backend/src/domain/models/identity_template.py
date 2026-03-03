import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, Text
from sqlmodel import Field, Relationship, SQLModel


class IdentityTemplateBase(SQLModel):
    criminal_id: uuid.UUID = Field(foreign_key="criminals.id", index=True, unique=True)
    template_version: str = "tracenet_template_v1"
    embedding_version: str = "tracenet_v1"
    primary_face_id: Optional[uuid.UUID] = Field(default=None, index=True)
    included_face_ids: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    support_face_ids: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    archived_face_ids: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    outlier_face_ids: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    active_face_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    support_face_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    archived_face_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    outlier_face_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))


class IdentityTemplate(IdentityTemplateBase, table=True):
    __tablename__ = "identity_templates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    template_embedding: List[float] = Field(sa_column=Column(Vector(512), nullable=False))

    criminal: Optional["Criminal"] = Relationship(back_populates="identity_template")
