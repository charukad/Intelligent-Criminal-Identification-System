from dataclasses import dataclass, field
from typing import Literal

import cv2
import numpy as np

REJECTION_REASON_PRIORITY = {
    "invalid_face_crop": 0,
    "image_too_dark": 1,
    "image_too_bright": 2,
    "face_too_small": 3,
    "extreme_face_pose": 4,
    "facial_features_obscured": 5,
    "face_too_blurry": 6,
}

WARNING_PRIORITY = {
    "poor_lighting": 0,
    "face_pose_off_center": 1,
    "possible_face_occlusion": 2,
    "face_is_blurry": 3,
    "face_small_in_frame": 4,
}


def sort_rejection_reasons(reasons: list[str]) -> list[str]:
    return sorted(
        set(reasons),
        key=lambda reason: (REJECTION_REASON_PRIORITY.get(reason, 999), reason),
    )


def sort_quality_warnings(warnings: list[str]) -> list[str]:
    return sorted(
        set(warnings),
        key=lambda warning: (WARNING_PRIORITY.get(warning, 999), warning),
    )


@dataclass(frozen=True)
class FaceQualityReport:
    status: Literal["accepted", "accepted_with_warnings", "rejected"]
    quality_score: float
    blur_score: float
    brightness_score: float
    face_area_ratio: float
    warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    pose_score: float = 100.0
    occlusion_score: float = 100.0

    @property
    def should_reject(self) -> bool:
        return self.status == "rejected"

    @property
    def primary_rejection_reason(self) -> str | None:
        if not self.rejection_reasons:
            return None
        return sort_rejection_reasons(self.rejection_reasons)[0]


class FaceQualityAssessor:
    MIN_FACE_DIMENSION_REJECT = 40
    MIN_FACE_AREA_RATIO_REJECT = 0.03
    MIN_FACE_AREA_RATIO_WARN = 0.08

    MIN_BLUR_SCORE_REJECT = 40.0
    MIN_BLUR_SCORE_WARN = 80.0

    MIN_BRIGHTNESS_REJECT = 45.0
    MAX_BRIGHTNESS_REJECT = 210.0
    MIN_BRIGHTNESS_WARN = 70.0
    MAX_BRIGHTNESS_WARN = 185.0

    MAX_ROLL_WARN_DEGREES = 10.0
    MAX_ROLL_REJECT_DEGREES = 18.0
    MAX_YAW_WARN = 0.22
    MAX_YAW_REJECT = 0.35

    MIN_OCCLUSION_SCORE_WARN = 55.0
    MIN_OCCLUSION_SCORE_REJECT = 30.0
    MIN_VISIBLE_LANDMARK_RATIO_WARN = 0.7
    MIN_VISIBLE_LANDMARK_RATIO_REJECT = 0.45

    def assess(
        self,
        image: np.ndarray,
        box: tuple[int, int, int, int],
        *,
        landmarks: list[tuple[float, float]] | None = None,
    ) -> FaceQualityReport:
        image_height, image_width = image.shape[:2]
        x, y, w, h = (int(value) for value in box)

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(image_width, x + w)
        y2 = min(image_height, y + h)
        face_crop = image[y1:y2, x1:x2]

        if face_crop.size == 0:
            return FaceQualityReport(
                status="rejected",
                quality_score=0.0,
                blur_score=0.0,
                brightness_score=0.0,
                face_area_ratio=0.0,
                rejection_reasons=["invalid_face_crop"],
            )

        gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)
        blur_score = float(cv2.Laplacian(gray_crop, cv2.CV_64F).var())
        brightness_score = float(gray_crop.mean())
        face_area_ratio = float((w * h) / max(image_width * image_height, 1))
        pose_metrics = self._compute_pose_metrics(landmarks)
        occlusion_metrics = self._compute_occlusion_metrics(gray_crop, box, landmarks)
        pose_score = float(pose_metrics["pose_score"]) if pose_metrics else 100.0
        occlusion_score = float(occlusion_metrics["occlusion_score"]) if occlusion_metrics else 100.0

        warnings: list[str] = []
        rejection_reasons: list[str] = []

        if w < self.MIN_FACE_DIMENSION_REJECT or h < self.MIN_FACE_DIMENSION_REJECT:
            rejection_reasons.append("face_too_small")
        elif face_area_ratio < self.MIN_FACE_AREA_RATIO_WARN:
            warnings.append("face_small_in_frame")

        if face_area_ratio < self.MIN_FACE_AREA_RATIO_REJECT:
            rejection_reasons.append("face_too_small")

        if blur_score < self.MIN_BLUR_SCORE_REJECT:
            rejection_reasons.append("face_too_blurry")
        elif blur_score < self.MIN_BLUR_SCORE_WARN:
            warnings.append("face_is_blurry")

        if brightness_score < self.MIN_BRIGHTNESS_REJECT:
            rejection_reasons.append("image_too_dark")
        elif brightness_score > self.MAX_BRIGHTNESS_REJECT:
            rejection_reasons.append("image_too_bright")
        elif (
            brightness_score < self.MIN_BRIGHTNESS_WARN
            or brightness_score > self.MAX_BRIGHTNESS_WARN
        ):
            warnings.append("poor_lighting")

        if pose_metrics:
            roll_angle = float(pose_metrics["roll_angle_degrees"])
            yaw_asymmetry = float(pose_metrics["yaw_asymmetry"])
            if roll_angle > self.MAX_ROLL_REJECT_DEGREES or yaw_asymmetry > self.MAX_YAW_REJECT:
                rejection_reasons.append("extreme_face_pose")
            elif roll_angle > self.MAX_ROLL_WARN_DEGREES or yaw_asymmetry > self.MAX_YAW_WARN:
                warnings.append("face_pose_off_center")

        if occlusion_metrics:
            visible_landmark_ratio = float(occlusion_metrics["visible_landmark_ratio"])
            if (
                occlusion_score < self.MIN_OCCLUSION_SCORE_REJECT
                or visible_landmark_ratio < self.MIN_VISIBLE_LANDMARK_RATIO_REJECT
            ):
                rejection_reasons.append("facial_features_obscured")
            elif (
                occlusion_score < self.MIN_OCCLUSION_SCORE_WARN
                or visible_landmark_ratio < self.MIN_VISIBLE_LANDMARK_RATIO_WARN
            ):
                warnings.append("possible_face_occlusion")

        quality_score = self._compute_quality_score(
            blur_score=blur_score,
            brightness_score=brightness_score,
            face_area_ratio=face_area_ratio,
            pose_score=pose_score,
            occlusion_score=occlusion_score,
        )

        if rejection_reasons:
            status: Literal["accepted", "accepted_with_warnings", "rejected"] = "rejected"
        elif warnings:
            status = "accepted_with_warnings"
        else:
            status = "accepted"

        return FaceQualityReport(
            status=status,
            quality_score=quality_score,
            blur_score=round(blur_score, 4),
            brightness_score=round(brightness_score, 4),
            face_area_ratio=round(face_area_ratio, 6),
            warnings=sort_quality_warnings(warnings),
            rejection_reasons=sort_rejection_reasons(rejection_reasons),
            pose_score=round(pose_score, 2),
            occlusion_score=round(occlusion_score, 2),
        )

    def _compute_quality_score(
        self,
        *,
        blur_score: float,
        brightness_score: float,
        face_area_ratio: float,
        pose_score: float,
        occlusion_score: float,
    ) -> float:
        sharpness_component = min(1.0, blur_score / 120.0)
        lighting_component = max(0.0, 1.0 - (abs(brightness_score - 128.0) / 128.0))
        size_component = min(1.0, face_area_ratio / 0.2)
        pose_component = max(0.0, min(1.0, pose_score / 100.0))
        occlusion_component = max(0.0, min(1.0, occlusion_score / 100.0))
        score = (
            (0.28 * sharpness_component)
            + (0.24 * lighting_component)
            + (0.14 * size_component)
            + (0.18 * pose_component)
            + (0.16 * occlusion_component)
        )
        return round(score * 100.0, 2)

    def _compute_pose_metrics(
        self,
        landmarks: list[tuple[float, float]] | None,
    ) -> dict[str, float] | None:
        points = self._parse_landmarks(landmarks)
        if points is None:
            return None

        left_eye, right_eye, nose, left_mouth, right_mouth = points
        eye_delta = right_eye - left_eye
        eye_distance = max(float(np.linalg.norm(eye_delta)), 1e-6)
        roll_angle_degrees = abs(float(np.degrees(np.arctan2(eye_delta[1], eye_delta[0]))))
        left_eye_to_nose = abs(float(nose[0] - left_eye[0]))
        right_eye_to_nose = abs(float(right_eye[0] - nose[0]))
        yaw_asymmetry = abs(left_eye_to_nose - right_eye_to_nose) / eye_distance

        roll_component = min(1.0, roll_angle_degrees / self.MAX_ROLL_REJECT_DEGREES)
        yaw_component = min(1.0, yaw_asymmetry / self.MAX_YAW_REJECT)
        pose_score = max(0.0, 100.0 * (1.0 - ((0.45 * roll_component) + (0.55 * yaw_component))))

        return {
            "pose_score": pose_score,
            "roll_angle_degrees": roll_angle_degrees,
            "yaw_asymmetry": yaw_asymmetry,
        }

    def _compute_occlusion_metrics(
        self,
        gray_crop: np.ndarray,
        box: tuple[int, int, int, int],
        landmarks: list[tuple[float, float]] | None,
    ) -> dict[str, float] | None:
        points = self._parse_landmarks(landmarks)
        if points is None:
            return None

        crop_height, crop_width = gray_crop.shape[:2]
        x, y, _w, _h = (int(value) for value in box)
        patch_radius = max(4, int(min(crop_height, crop_width) * 0.08))
        visibility_scores: list[float] = []

        for point in points:
            rel_x = int(round(float(point[0] - x)))
            rel_y = int(round(float(point[1] - y)))

            min_margin = min(rel_x, rel_y, (crop_width - 1) - rel_x, (crop_height - 1) - rel_y)
            if min_margin < patch_radius * 0.5:
                visibility_scores.append(0.0)
                continue

            x1 = max(0, rel_x - patch_radius)
            y1 = max(0, rel_y - patch_radius)
            x2 = min(crop_width, rel_x + patch_radius + 1)
            y2 = min(crop_height, rel_y + patch_radius + 1)
            patch = gray_crop[y1:y2, x1:x2]
            if patch.size == 0:
                visibility_scores.append(0.0)
                continue

            local_contrast = float(np.std(patch))
            local_sharpness = float(cv2.Laplacian(patch, cv2.CV_64F).var())
            clipped_ratio = float(np.mean((patch <= 10) | (patch >= 245)))

            contrast_component = min(1.0, local_contrast / 24.0)
            sharpness_component = min(1.0, local_sharpness / 60.0)
            exposure_component = max(0.0, 1.0 - clipped_ratio)
            visibility_scores.append(
                (0.45 * contrast_component)
                + (0.35 * sharpness_component)
                + (0.20 * exposure_component)
            )

        if not visibility_scores:
            return None

        visible_landmark_ratio = sum(score >= 0.35 for score in visibility_scores) / len(visibility_scores)
        occlusion_score = float(np.mean(visibility_scores) * 100.0)
        return {
            "occlusion_score": occlusion_score,
            "visible_landmark_ratio": visible_landmark_ratio,
        }

    def _parse_landmarks(
        self,
        landmarks: list[tuple[float, float]] | None,
    ) -> np.ndarray | None:
        if landmarks is None:
            return None

        points = np.asarray(landmarks, dtype=np.float32)
        if points.shape != (5, 2):
            return None
        return points
