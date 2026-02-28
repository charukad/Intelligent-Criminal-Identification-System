from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col, func

from src.infrastructure.database import get_db
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.audit import AuditRepository
from src.services.criminal_service import CriminalService
from src.services.face_enrollment_service import FaceEnrollmentService
from src.services.ai.runtime import pipeline
from src.schemas.criminal import CriminalCreate, CriminalResponse, CriminalUpdate, CriminalListResponse, CriminalFaceResponse
from src.api.deps import get_current_user, get_officer_or_above, get_admin_or_senior_officer
from src.domain.models.user import User
from src.domain.models.criminal import Criminal, ThreatLevel, LegalStatus

router = APIRouter()


def serialize_face(face: Any) -> dict[str, Any]:
    return {
        "id": face.id,
        "criminal_id": face.criminal_id,
        "image_url": face.image_url,
        "is_primary": face.is_primary,
        "embedding_version": face.embedding_version,
        "created_at": face.created_at,
        "box": (
            face.box_x if face.box_x is not None else 0,
            face.box_y if face.box_y is not None else 0,
            face.box_w if face.box_w is not None else 0,
            face.box_h if face.box_h is not None else 0,
        ),
    }


def serialize_criminal(criminal: Criminal, primary_face_image_url: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": criminal.id,
        "nic": criminal.nic,
        "first_name": criminal.first_name,
        "last_name": criminal.last_name,
        "aliases": criminal.aliases,
        "dob": criminal.dob,
        "gender": criminal.gender,
        "blood_type": criminal.blood_type,
        "last_known_address": criminal.last_known_address,
        "status": criminal.status,
        "threat_level": criminal.threat_level,
        "physical_description": criminal.physical_description,
        "primary_face_image_url": primary_face_image_url,
    }

@router.get("/", response_model=CriminalListResponse)
async def list_criminals(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None, min_length=1),
    threat_level: Optional[ThreatLevel] = None,
    status: Optional[LegalStatus] = None,
    legal_status: Optional[LegalStatus] = None,  # Backwards compatibility
    current_user: User = Depends(get_current_user),  # All authenticated users can view
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List criminals with pagination and optional filters.
    Filters: search query, threat level, legal status.
    """
    effective_status = status or legal_status
    filters = []
    if q:
        filters.append(
            (col(Criminal.first_name).ilike(f"%{q}%")) |
            (col(Criminal.last_name).ilike(f"%{q}%")) |
            (col(Criminal.nic).ilike(f"%{q}%"))
        )
    if threat_level:
        filters.append(Criminal.threat_level == threat_level)
    if effective_status:
        filters.append(Criminal.status == effective_status)

    count_query = select(func.count()).select_from(Criminal)
    if filters:
        count_query = count_query.where(*filters)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    data_query = select(Criminal)
    if filters:
        data_query = data_query.where(*filters)
    data_query = data_query.offset((page - 1) * limit).limit(limit)
    data_result = await db.execute(data_query)
    items = data_result.scalars().all()

    face_repo = FaceRepository(db)
    primary_faces = await face_repo.get_primary_faces_for_criminals([criminal.id for criminal in items])
    primary_face_map = {
        face.criminal_id: face.image_url
        for face in primary_faces
    }

    serialized_items = [
        serialize_criminal(
            criminal,
            primary_face_image_url=primary_face_map.get(criminal.id),
        )
        for criminal in items
    ]

    pages = max(1, (total + limit - 1) // limit)
    return {"items": serialized_items, "total": total, "page": page, "pages": pages}

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
    criminal = await service.get_criminal_details(criminal_id)
    face_repo = FaceRepository(db)
    primary_faces = await face_repo.get_primary_faces_for_criminals([criminal.id])
    primary_face_image_url = primary_faces[0].image_url if primary_faces else None
    return serialize_criminal(criminal, primary_face_image_url=primary_face_image_url)

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
    
    updated = await repo.update(criminal)
    face_repo = FaceRepository(db)
    primary_faces = await face_repo.get_primary_faces_for_criminals([updated.id])
    primary_face_image_url = primary_faces[0].image_url if primary_faces else None
    return serialize_criminal(updated, primary_face_image_url=primary_face_image_url)

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


@router.post("/{criminal_id}/faces", response_model=CriminalFaceResponse)
async def enroll_criminal_face(
    criminal_id: UUID,
    file: UploadFile = File(...),
    is_primary: bool = Form(False),
    current_user: User = Depends(get_officer_or_above()),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Upload a single-face image for a criminal and store its TraceNet embedding.
    Requires: Admin, Senior Officer, or Field Officer role.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    face_repo = FaceRepository(db)
    criminal_repo = CriminalRepository(db)
    audit_repo = AuditRepository(db)
    service = FaceEnrollmentService(pipeline, face_repo, criminal_repo, audit_repo)

    try:
        return await service.enroll_face(
            criminal_id=criminal_id,
            image_bytes=content,
            filename=file.filename,
            is_primary=is_primary,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{criminal_id}/faces", response_model=List[CriminalFaceResponse])
async def list_criminal_faces(
    criminal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    List enrolled face images and embedding metadata for a criminal.
    All authenticated users can view criminal face records.
    """
    criminal_repo = CriminalRepository(db)
    criminal = await criminal_repo.get(criminal_id)
    if not criminal:
        raise HTTPException(status_code=404, detail="Criminal not found")

    face_repo = FaceRepository(db)
    faces = await face_repo.list_by_criminal(criminal_id)
    return [serialize_face(face) for face in faces]


@router.delete("/{criminal_id}/faces/{face_id}")
async def delete_criminal_face(
    criminal_id: UUID,
    face_id: UUID,
    current_user: User = Depends(get_officer_or_above()),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete an enrolled face image and its embedding record.
    If the deleted face was primary, another stored face is promoted automatically.
    """
    face_repo = FaceRepository(db)
    criminal_repo = CriminalRepository(db)
    audit_repo = AuditRepository(db)
    service = FaceEnrollmentService(pipeline, face_repo, criminal_repo, audit_repo)

    try:
        return await service.delete_face(
            criminal_id=criminal_id,
            face_id=face_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{criminal_id}/faces/{face_id}/primary")
async def set_criminal_face_as_primary(
    criminal_id: UUID,
    face_id: UUID,
    current_user: User = Depends(get_officer_or_above()),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Mark an existing enrolled face image as the primary face record.
    """
    face_repo = FaceRepository(db)
    criminal_repo = CriminalRepository(db)
    audit_repo = AuditRepository(db)
    service = FaceEnrollmentService(pipeline, face_repo, criminal_repo, audit_repo)

    try:
        return await service.set_primary_face(
            criminal_id=criminal_id,
            face_id=face_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
