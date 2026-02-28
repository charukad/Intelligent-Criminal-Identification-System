from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.audit import AuditRepository
from src.services.ai.runtime import pipeline
from src.services.recognition_service import RecognitionService
from src.api.deps import get_current_user
from src.domain.models.user import User

router = APIRouter()

@router.post("/identify")
async def identify_suspect(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Identify faces in an uploaded image.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="File must be an image")
        
    content = await file.read()
    
    face_repo = FaceRepository(db)
    criminal_repo = CriminalRepository(db)
    audit_repo = AuditRepository(db)
    
    service = RecognitionService(pipeline, face_repo, criminal_repo, audit_repo)
    
    try:
        results = await service.identify_suspects(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"results": results}
