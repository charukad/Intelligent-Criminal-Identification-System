from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.infrastructure.database import get_db
from src.api.deps import get_current_user, get_admin_or_senior_officer
from src.domain.models.user import User
from src.domain.models.station import StationBase, Station

router = APIRouter()

@router.get("/", response_model=List[Station])
async def get_stations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get all stations.
    """
    result = await db.execute(select(Station))
    return result.scalars().all()

@router.post("/", response_model=Station)
async def create_station(
    station_in: StationBase,
    current_user: User = Depends(get_admin_or_senior_officer()),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new station. Admin or Senior Officer only.
    """
    station_obj = Station.model_validate(station_in)
    db.add(station_obj)
    await db.commit()
    await db.refresh(station_obj)
    return station_obj
