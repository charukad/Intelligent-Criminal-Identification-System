from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from src.domain.models.audit import AuditLog

class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recent_identifications_count(self, hours: int = 24) -> int:
        from datetime import datetime, timedelta
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query = select(AuditLog).where(AuditLog.action == "IDENTIFY").where(AuditLog.timestamp >= time_threshold)
        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def create(self, audit: AuditLog) -> AuditLog:
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(audit)
        return audit
