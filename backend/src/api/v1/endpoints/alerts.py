from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc

from src.infrastructure.database import get_db
from src.api.deps import get_current_user
from src.domain.models.user import User
from src.domain.models.alert import Alert

router = APIRouter()

@router.get("/", response_model=List[Alert])
async def get_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get active alerts.
    """
    query = select(Alert).where(Alert.is_resolved == False).order_by(desc(Alert.timestamp))
    result = await db.execute(query)
    return result.scalars().all()
