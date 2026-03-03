from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.domain.models.review_case import ReviewCase, ReviewCaseStatus, ReviewCaseType
from src.infrastructure.repositories.base import BaseRepository


class ReviewCaseRepository(BaseRepository[ReviewCase]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewCase)

    async def list_cases(
        self,
        *,
        case_type: ReviewCaseType | None = None,
        status: ReviewCaseStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ReviewCase]:
        statement = select(ReviewCase)
        if case_type is not None:
            statement = statement.where(ReviewCase.case_type == case_type)
        if status is not None:
            statement = statement.where(ReviewCase.status == status)
        statement = (
            statement
            .order_by(ReviewCase.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_open_duplicate_case(
        self,
        source_criminal_id: UUID,
        matched_criminal_id: UUID,
    ) -> ReviewCase | None:
        statement = (
            select(ReviewCase)
            .where(ReviewCase.case_type == ReviewCaseType.DUPLICATE_IDENTITY)
            .where(ReviewCase.status == ReviewCaseStatus.OPEN)
            .where(ReviewCase.source_criminal_id == source_criminal_id)
            .where(ReviewCase.matched_criminal_id == matched_criminal_id)
            .order_by(ReviewCase.created_at.desc())
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def resolve_case(
        self,
        case: ReviewCase,
        *,
        status: ReviewCaseStatus,
        resolved_by_id: UUID | None,
        resolution_notes: str | None = None,
    ) -> ReviewCase:
        case.status = status
        case.resolved_by_id = resolved_by_id
        case.resolution_notes = resolution_notes
        case.resolved_at = datetime.now(timezone.utc)
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        return case
