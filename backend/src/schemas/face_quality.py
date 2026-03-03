from typing import Literal

from pydantic import BaseModel


class FaceQualityResponse(BaseModel):
    status: Literal["accepted", "accepted_with_warnings", "rejected"]
    quality_score: float
    blur_score: float
    brightness_score: float
    face_area_ratio: float
    pose_score: float
    occlusion_score: float
    warnings: list[str]


class FaceQualityPreviewResponse(BaseModel):
    status: Literal["accepted", "accepted_with_warnings", "rejected"]
    detected_face_count: int
    decision_reason: str
    message: str
    box: tuple[int, int, int, int] | None = None
    quality: FaceQualityResponse | None = None
