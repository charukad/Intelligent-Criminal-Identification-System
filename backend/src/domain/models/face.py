import uuid
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector

class FaceEmbeddingBase(SQLModel):
    image_url: str
    is_primary: bool = False
    embedding_version: str = "v1"

class FaceEmbedding(FaceEmbeddingBase, table=True):
    __tablename__ = "face_embeddings"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    criminal_id: uuid.UUID = Field(foreign_key="criminals.id")
    
    # 512-dimension vector
    embedding: List[float] = Field(sa_column=Column(Vector(512))) 
    
    # Relationships
    criminal: Optional["Criminal"] = Relationship(back_populates="faces")
