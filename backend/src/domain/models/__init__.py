# Import all models in the correct order to ensure SQLAlchemy can resolve relationships
# Base models without dependencies first
from src.domain.models.station import Station, StationBase
from src.domain.models.criminal import Criminal
from src.domain.models.user import User, UserRole, UserBase
from src.domain.models.case import Case, CaseStatus, Offense

# Import face model when pgvector is available
from src.domain.models.face import FaceEmbedding

__all__ = [
    "Station",
    "StationBase",
    "User",
    "UserRole",
    "UserBase",
    "Criminal",
    "Case",
    "CaseStatus",
    "Offense",
]
