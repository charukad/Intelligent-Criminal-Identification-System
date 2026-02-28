import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime
from pgvector.sqlalchemy import Vector

class FaceEmbeddingBase(SQLModel):
    image_url: str
    is_primary: bool = False
    embedding_version: str = "v1"
    box_x: Optional[int] = None
    box_y: Optional[int] = None
    box_w: Optional[int] = None
    box_h: Optional[int] = None

class FaceEmbedding(FaceEmbeddingBase, table=True):
    __tablename__ = "face_embeddings"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    criminal_id: uuid.UUID = Field(foreign_key="criminals.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    
    # 512-dimension vector
    embedding: List[float] = Field(sa_column=Column(Vector(512))) 
    
    # Relationships
    criminal: Optional["Criminal"] = Relationship(back_populates="faces")
