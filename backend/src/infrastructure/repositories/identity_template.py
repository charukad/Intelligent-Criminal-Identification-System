from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.domain.models.identity_template import IdentityTemplate
from src.infrastructure.repositories.base import BaseRepository


class IdentityTemplateRepository(BaseRepository[IdentityTemplate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, IdentityTemplate)

    async def get_by_criminal(self, criminal_id: UUID) -> Optional[IdentityTemplate]:
        statement = select(IdentityTemplate).where(IdentityTemplate.criminal_id == criminal_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def find_nearest_neighbors(
        self,
        query_vector: List[float],
        limit: int = 5,
    ) -> List[Tuple[IdentityTemplate, float]]:
        statement = (
            select(
                IdentityTemplate,
                IdentityTemplate.template_embedding.l2_distance(query_vector).label("distance"),
            )
            .order_by(IdentityTemplate.template_embedding.l2_distance(query_vector))
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.all()

    async def upsert_template(
        self,
        criminal_id: UUID,
        template_data: dict[str, Any],
    ) -> IdentityTemplate:
        template = await self.get_by_criminal(criminal_id)
        timestamp = datetime.now(timezone.utc)

        if template is None:
            template = IdentityTemplate(
                criminal_id=criminal_id,
                updated_at=timestamp,
                **template_data,
            )
            self.session.add(template)
        else:
            for field, value in template_data.items():
                setattr(template, field, value)
            template.updated_at = timestamp
            self.session.add(template)

        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete_by_criminal(self, criminal_id: UUID) -> bool:
        template = await self.get_by_criminal(criminal_id)
        if template is None:
            return False

        await self.session.delete(template)
        await self.session.commit()
        return True
