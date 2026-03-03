import numpy as np
import cv2

from src.services.ai.face_quality import FaceQualityAssessor


def build_face_image() -> np.ndarray:
    image = np.full((220, 220, 3), 128, dtype=np.uint8)
    for row in range(40, 180, 8):
        for col in range(40, 180, 8):
            value = 70 if (row + col) % 16 == 0 else 185
            image[row:row + 4, col:col + 4] = value
    return image


def build_landmarks() -> list[tuple[float, float]]:
    return [
        (80.0, 90.0),
        (140.0, 90.0),
        (110.0, 120.0),
        (88.0, 146.0),
        (132.0, 146.0),
    ]


def test_face_quality_assessor_accepts_clear_well_lit_face():
    assessor = FaceQualityAssessor()
    image = build_face_image()
    landmarks = build_landmarks()

    report = assessor.assess(image, (50, 60, 120, 120), landmarks=landmarks)

    assert report.status in {"accepted", "accepted_with_warnings"}
    assert report.quality_score > 0
    assert report.pose_score > 70
    assert report.occlusion_score > 50
    assert "image_too_dark" not in report.rejection_reasons


def test_face_quality_assessor_rejects_dark_face_crop():
    assessor = FaceQualityAssessor()
    image = np.zeros((200, 200, 3), dtype=np.uint8)

    report = assessor.assess(image, (40, 40, 120, 120))

    assert report.status == "rejected"
    assert "image_too_dark" in report.rejection_reasons
    assert "face_too_blurry" in report.rejection_reasons
    assert report.primary_rejection_reason == "image_too_dark"


def test_face_quality_assessor_rejects_extreme_face_pose():
    assessor = FaceQualityAssessor()
    image = build_face_image()
    landmarks = [
        (74.0, 110.0),
        (122.0, 86.0),
        (98.0, 124.0),
        (85.0, 152.0),
        (122.0, 130.0),
    ]

    report = assessor.assess(image, (50, 60, 120, 120), landmarks=landmarks)

    assert report.status == "rejected"
    assert "extreme_face_pose" in report.rejection_reasons
    assert report.pose_score <= 55


def test_face_quality_assessor_rejects_obscured_landmark_regions():
    assessor = FaceQualityAssessor()
    image = build_face_image()
    landmarks = build_landmarks()

    for x, y in landmarks[:3]:
        x1 = int(x) - 10
        y1 = int(y) - 10
        image[y1:y1 + 20, x1:x1 + 20] = 0

    report = assessor.assess(image, (50, 60, 120, 120), landmarks=landmarks)

    assert report.status == "rejected"
    assert "facial_features_obscured" in report.rejection_reasons
    assert report.occlusion_score <= 40


def test_face_quality_assessor_sorts_warnings_by_priority():
    assessor = FaceQualityAssessor()
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    image[20:100, 20:100] = 60

    for row in range(20, 100, 4):
        for col in range(20, 100, 4):
            value = 35 if (row + col) % 8 == 0 else 85
            image[row:row + 2, col:col + 2] = value
    image[20:100, 20:100] = cv2.GaussianBlur(image[20:100, 20:100], (5, 5), 0)

    report = assessor.assess(image, (20, 20, 80, 80))

    assert report.status == "accepted_with_warnings"
    assert report.warnings == ["poor_lighting", "face_is_blurry", "face_small_in_frame"]
