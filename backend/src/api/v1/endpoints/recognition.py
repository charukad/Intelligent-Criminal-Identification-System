from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.services.ai.strategies import MTCNNStrategy, InceptionResnetStrategy
from src.services.ai.pipeline import FaceProcessingPipeline
from src.services.recognition_service import RecognitionService
from src.api.deps import get_current_user
from src.domain.models.user import User

router = APIRouter()

# Instantiate AI components globally (or singleton dependency) to avoid reloading models on every request
# In production, use @lru_cache or FastAPI dependency overrides for testing
mtcnn = MTCNNStrategy()
resnet = InceptionResnetStrategy()
pipeline = FaceProcessingPipeline(mtcnn, resnet)

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
    
    service = RecognitionService(pipeline, face_repo, criminal_repo)
    
    results = await service.identify_suspects(content)
    return {"results": results}
