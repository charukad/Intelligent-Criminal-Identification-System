from typing import Any

import cv2
import numpy as np

from src.services.ai.face_quality import FaceQualityAssessor, FaceQualityReport, sort_quality_warnings
from src.services.ai.pipeline import FaceProcessingPipeline


QUALITY_REASON_MESSAGES = {
    "accepted": "Image is suitable for enrollment.",
    "accepted_with_warnings": "Image can be enrolled, but quality warnings should be reviewed.",
    "no_face": "No face was detected in the cropped image.",
    "multiple_faces": "Multiple faces were detected. Crop tighter to include only one subject.",
    "invalid_face_crop": "The detected face crop is invalid.",
    "face_too_small": "The face is too small in the frame. Use a tighter crop.",
    "face_too_blurry": "The face image is too blurry for reliable enrollment.",
    "image_too_dark": "The image is too dark for reliable enrollment.",
    "image_too_bright": "The image is too bright for reliable enrollment.",
    "extreme_face_pose": "The face angle is too extreme for reliable enrollment. Use a straighter pose.",
    "facial_features_obscured": "Key facial features are obscured or cropped out. Use a clearer face image.",
    "face_pose_off_center": "The face angle is off-center. A straighter pose will enroll more reliably.",
    "possible_face_occlusion": "Some facial features may be blocked or cropped too tightly.",
}


def get_quality_reason_message(reason: str) -> str:
    return QUALITY_REASON_MESSAGES.get(reason, "The image failed face quality checks.")


def serialize_quality_report(quality_report: FaceQualityReport) -> dict[str, Any]:
    return {
        "status": quality_report.status,
        "quality_score": quality_report.quality_score,
        "blur_score": quality_report.blur_score,
        "brightness_score": quality_report.brightness_score,
        "face_area_ratio": quality_report.face_area_ratio,
        "pose_score": quality_report.pose_score,
        "occlusion_score": quality_report.occlusion_score,
        "warnings": sort_quality_warnings(quality_report.warnings),
    }


class FaceQualityService:
    def __init__(
        self,
        pipeline: FaceProcessingPipeline,
        quality_assessor: FaceQualityAssessor | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.quality_assessor = quality_assessor or FaceQualityAssessor()

    def preview_image(self, image_bytes: bytes) -> dict[str, Any]:
        image = self._decode_image(image_bytes)
        face_regions = self.pipeline.extract_face_regions(image)

        if not face_regions:
            return {
                "status": "rejected",
                "detected_face_count": 0,
                "decision_reason": "no_face",
                "message": get_quality_reason_message("no_face"),
                "box": None,
                "quality": None,
            }

        if len(face_regions) > 1:
            return {
                "status": "rejected",
                "detected_face_count": len(face_regions),
                "decision_reason": "multiple_faces",
                "message": get_quality_reason_message("multiple_faces"),
                "box": None,
                "quality": None,
            }

        face_region = face_regions[0]
        quality_report = self.quality_assessor.assess(
            image,
            face_region["box"],
            landmarks=face_region.get("landmarks"),
        )
        decision_reason = quality_report.primary_rejection_reason or quality_report.status

        return {
            "status": quality_report.status,
            "detected_face_count": 1,
            "decision_reason": decision_reason,
            "message": get_quality_reason_message(decision_reason),
            "box": face_region["box"],
            "quality": serialize_quality_report(quality_report),
        }

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_np is None:
            raise ValueError("Invalid image data")
        return cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
