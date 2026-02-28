from typing import Optional
import uuid
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field

class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertBase(SQLModel):
    title: str
    message: str
    severity: AlertSeverity = Field(default=AlertSeverity.INFO)
    is_resolved: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    criminal_id: Optional[uuid.UUID] = Field(default=None, foreign_key="criminals.id")
    resolved_by_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

class Alert(AlertBase, table=True):
    __tablename__ = "alerts"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
