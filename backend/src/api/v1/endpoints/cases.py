from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.infrastructure.database import get_db
from src.api.deps import get_current_user, get_officer_or_above
from src.domain.models.user import User
from src.domain.models.case import CaseBase, Case, CaseStatus

router = APIRouter()

@router.get("/", response_model=List[Case])
async def get_cases(
    status: CaseStatus = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get all cases, optionally filtered by status.
    """
    query = select(Case)
    if status is not None:
        query = query.where(Case.status == status)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=Case)
async def create_case(
    case_in: CaseBase,
    current_user: User = Depends(get_officer_or_above()),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new case. Officer or above.
    """
    case_obj = Case.model_validate(case_in)
    db.add(case_obj)
    await db.commit()
    await db.refresh(case_obj)
    return case_obj
