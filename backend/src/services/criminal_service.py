import uuid
from typing import List, Optional
from sqlalchemy.exc import DBAPIError, IntegrityError
from fastapi import HTTPException, status

from src.domain.models.criminal import Criminal, CriminalBase, ThreatLevel
from src.domain.models.case import Offense # Fix: Offense is in case.py
from src.infrastructure.repositories.criminal import CriminalRepository
from src.core.logging import logger

class CriminalService:
    def __init__(self, criminal_repo: CriminalRepository):
        self.criminal_repo = criminal_repo

    async def create_profile(self, criminal_in: Criminal) -> Criminal:
        """
        Creates a new criminal profile with validation.
        """
        try:
            # Check for existing NIC to prevent duplicates at application level
            if criminal_in.nic:
                existing = await self.criminal_repo.get_by_nic(criminal_in.nic)
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Criminal with NIC {criminal_in.nic} already exists."
                    )
            
            created_criminal = await self.criminal_repo.create(criminal_in)
            logger.info(f"Created new criminal profile: {created_criminal.id} ({created_criminal.first_name})")
            return created_criminal
            
        except IntegrityError as e:
            logger.error(f"Database integrity error creating criminal: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation."
            )
        except Exception as e:
            logger.error(f"Unexpected error creating criminal: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while creating profile."
            )

    async def get_criminal_details(self, criminal_id: uuid.UUID) -> Criminal:
        """
        Retrieves a full dossier. Raises 404 if not found.
        """
        criminal = await self.criminal_repo.get(criminal_id)
        if not criminal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Criminal profile not found"
            )
        return criminal

    async def search_criminals(self, query: str) -> List[Criminal]:
        """
        Performs a search for criminals by name or NIC.
        """
        return await self.criminal_repo.search_by_name(query)

    async def update_threat_level(self, criminal_id: uuid.UUID, level: ThreatLevel) -> Criminal:
        criminal = await self.get_criminal_details(criminal_id)
        criminal.threat_level = level
        updated = await self.criminal_repo.update(criminal, {"threat_level": level})
        logger.warning(f"Threat level updated for {criminal.id} to {level}")
        return updated
