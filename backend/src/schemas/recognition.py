from typing import Literal, Optional

from pydantic import BaseModel


class RecognitionCriminalSummary(BaseModel):
    id: str
    name: str
    nic: Optional[str] = None
    threat_level: Optional[str] = None


class RecognitionCandidate(BaseModel):
    criminal: RecognitionCriminalSummary
    face_id: str
    image_url: str
    is_primary: bool
    embedding_version: str
    distance: float


class RecognitionResult(BaseModel):
    box: tuple[int, int, int, int]
    status: Literal["match", "unknown"]
    confidence: float
    decision_reason: str
    distance: Optional[float] = None
    criminal: Optional[RecognitionCriminalSummary] = None


class RecognitionDebugFace(BaseModel):
    box: tuple[int, int, int, int]
    area: int
    selected: bool
    decision_reason: str
    best_distance: Optional[float] = None
    second_best_distance: Optional[float] = None
    top_candidates: list[RecognitionCandidate]


class RecognitionDebug(BaseModel):
    threshold: float
    ambiguity_margin: float
    single_face_only: bool
    detected_face_count: int
    analyzed_face_count: int
    faces: list[RecognitionDebugFace]


class RecognitionResponse(BaseModel):
    results: list[RecognitionResult]
    debug: Optional[RecognitionDebug] = None
