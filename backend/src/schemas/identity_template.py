from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IdentityTemplateResponse(BaseModel):
    id: UUID
    criminal_id: UUID
    template_version: str
    embedding_version: str
    primary_face_id: UUID | None = None
    included_face_ids: list[UUID] = []
    support_face_ids: list[UUID] = []
    archived_face_ids: list[UUID] = []
    outlier_face_ids: list[UUID] = []
    active_face_count: int
    support_face_count: int
    archived_face_count: int
    outlier_face_count: int
    updated_at: datetime
