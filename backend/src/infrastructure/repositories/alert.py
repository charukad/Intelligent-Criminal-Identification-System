from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from src.domain.models.alert import Alert

class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_alerts(self) -> List[Alert]:
        query = select(Alert).where(Alert.is_resolved == False).order_by(desc(Alert.timestamp))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, alert: Alert) -> Alert:
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def resolve(self, alert_id: UUID, resolved_by_id: UUID) -> Optional[Alert]:
        query = select(Alert).where(Alert.id == alert_id)
        result = await self.session.execute(query)
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_resolved = True
            alert.resolved_by_id = resolved_by_id
            await self.session.commit()
            await self.session.refresh(alert)
        return alert
