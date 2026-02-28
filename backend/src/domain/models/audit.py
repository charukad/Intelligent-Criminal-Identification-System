from typing import Optional
import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field

class AuditLogBase(SQLModel):
    action: str
    details: Optional[str] = None
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    criminal_id: Optional[uuid.UUID] = Field(default=None, foreign_key="criminals.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
