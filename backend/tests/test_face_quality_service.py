from unittest.mock import MagicMock, patch

import numpy as np

from src.services.ai.face_quality import FaceQualityReport
from src.services.face_quality_service import FaceQualityService


@patch("cv2.imdecode")
@patch("cv2.cvtColor")
def test_preview_image_returns_no_face_rejection(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.extract_face_regions.return_value = []

    service = FaceQualityService(pipeline)
    result = service.preview_image(b"fake-image")

    assert result["status"] == "rejected"
    assert result["detected_face_count"] == 0
    assert result["decision_reason"] == "no_face"


@patch("cv2.imdecode")
@patch("cv2.cvtColor")
def test_preview_image_returns_multiple_face_rejection(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.extract_face_regions.return_value = [
        {"box": (0, 0, 40, 40), "crop": np.zeros((40, 40, 3), dtype=np.uint8)},
        {"box": (50, 50, 40, 40), "crop": np.zeros((40, 40, 3), dtype=np.uint8)},
    ]

    service = FaceQualityService(pipeline)
    result = service.preview_image(b"fake-image")

    assert result["status"] == "rejected"
    assert result["detected_face_count"] == 2
    assert result["decision_reason"] == "multiple_faces"


@patch("cv2.imdecode")
@patch("cv2.cvtColor")
def test_preview_image_returns_quality_metrics(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.extract_face_regions.return_value = [
        {"box": (10, 20, 40, 50), "crop": np.zeros((50, 40, 3), dtype=np.uint8)},
    ]
    quality_assessor = MagicMock()
    quality_assessor.assess.return_value = FaceQualityReport(
        status="accepted_with_warnings",
        quality_score=88.0,
        blur_score=100.0,
        brightness_score=150.0,
        face_area_ratio=0.2,
        warnings=["poor_lighting"],
    )

    service = FaceQualityService(pipeline, quality_assessor=quality_assessor)
    result = service.preview_image(b"fake-image")

    assert result["status"] == "accepted_with_warnings"
    assert result["detected_face_count"] == 1
    assert result["decision_reason"] == "accepted_with_warnings"
    assert result["box"] == (10, 20, 40, 50)
    assert result["quality"]["pose_score"] == 100.0
    assert result["quality"]["occlusion_score"] == 100.0
    assert result["quality"]["warnings"] == ["poor_lighting"]


@patch("cv2.imdecode")
@patch("cv2.cvtColor")
def test_preview_image_uses_prioritized_rejection_reason(mock_cvtColor, mock_imdecode):
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline = MagicMock()
    pipeline.extract_face_regions.return_value = [
        {"box": (10, 20, 40, 50), "crop": np.zeros((50, 40, 3), dtype=np.uint8)},
    ]
    quality_assessor = MagicMock()
    quality_assessor.assess.return_value = FaceQualityReport(
        status="rejected",
        quality_score=10.0,
        blur_score=2.0,
        brightness_score=18.0,
        face_area_ratio=0.2,
        rejection_reasons=["face_too_blurry", "image_too_dark"],
    )

    service = FaceQualityService(pipeline, quality_assessor=quality_assessor)
    result = service.preview_image(b"fake-image")

    assert result["status"] == "rejected"
    assert result["decision_reason"] == "image_too_dark"
    assert result["message"] == "The image is too dark for reliable enrollment."
