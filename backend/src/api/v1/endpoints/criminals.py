from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.repositories.criminal import CriminalRepository
from src.services.criminal_service import CriminalService
from src.schemas.criminal import CriminalCreate, CriminalResponse, CriminalUpdate
from src.api.deps import get_current_user, get_officer_or_above, get_admin_or_senior_officer
from src.domain.models.user import User
from src.domain.models.criminal import Criminal

router = APIRouter()

@router.get("/", response_model=List[CriminalResponse])
async def search_criminals(
    q: str = Query(None, min_length=2),
    current_user: User = Depends(get_current_user),  # All authenticated users can view
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search criminals by name or NIC.
    All authenticated users can view criminal records.
    """
    repo = CriminalRepository(db)
    service = CriminalService(repo)
    if not q:
        return []
    return await service.search_criminals(q)

@router.post("/", response_model=CriminalResponse)
async def create_criminal(
    *,
    criminal_in: CriminalCreate,
    current_user: User = Depends(get_officer_or_above()),  # Officers and above can create
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create new criminal profile.
    Requires: Admin, Senior Officer, or Field Officer role.
    """
    repo = CriminalRepository(db)
    service = CriminalService(repo)
    
    criminal_obj = Criminal(
        nic=criminal_in.nic,
        first_name=criminal_in.first_name,
        last_name=criminal_in.last_name,
        aliases=criminal_in.aliases,
        dob=criminal_in.dob,
        gender=criminal_in.gender,
        blood_type=criminal_in.blood_type,
        last_known_address=criminal_in.last_known_address,
        status=criminal_in.status,
        threat_level=criminal_in.threat_level,
        physical_description=criminal_in.physical_description
    )
    
    return await service.create_profile(criminal_obj)

@router.get("/{criminal_id}", response_model=CriminalResponse)
async def read_criminal_by_id(
    criminal_id: UUID,
    current_user: User = Depends(get_current_user),  # All authenticated users can view
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get criminal details by ID.
    All authenticated users can view criminal records.
    """
    repo = CriminalRepository(db)
    service = CriminalService(repo)
    return await service.get_criminal_details(criminal_id)

@router.put("/{criminal_id}", response_model=CriminalResponse)
async def update_criminal(
    criminal_id: UUID,
    criminal_in: CriminalUpdate,
    current_user: User = Depends(get_officer_or_above()),  # Officers and above can update
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update criminal profile.
    Requires: Admin, Senior Officer, or Field Officer role.
    """
    repo = CriminalRepository(db)
    service = CriminalService(repo)
    
    criminal = await repo.get(criminal_id)
    if not criminal:
        raise HTTPException(status_code=404, detail="Criminal not found")
    
    # Update fields
    update_data = criminal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(criminal, field, value)
    
    return await repo.update(criminal)

@router.delete("/{criminal_id}")
async def delete_criminal(
    criminal_id: UUID,
    current_user: User = Depends(get_admin_or_senior_officer()),  # Admin and Senior Officer only
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete criminal record.
    Requires: Admin or Senior Officer role.
    """
    repo = CriminalRepository(db)
    service = CriminalService(repo)
    
    criminal = await repo.get(criminal_id)
    if not criminal:
        raise HTTPException(status_code=404, detail="Criminal not found")
    
    await repo.delete(criminal_id)
    return {"status": "success", "message": "Criminal record deleted"}
