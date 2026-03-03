from typing import Iterable

import cv2
import numpy as np


ALIGNMENT_OUTPUT_SIZE = (112, 112)
REFERENCE_5PTS = np.asarray(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


def align_face_to_template(
    image: np.ndarray,
    landmarks: Iterable[Iterable[float]],
    output_size: tuple[int, int] = ALIGNMENT_OUTPUT_SIZE,
) -> np.ndarray:
    points = np.asarray(list(landmarks), dtype=np.float32)
    if points.shape != (5, 2):
        raise ValueError("Expected exactly 5 facial landmarks for alignment")

    transform, _inliers = cv2.estimateAffinePartial2D(points, REFERENCE_5PTS, method=cv2.LMEDS)
    if transform is None:
        raise ValueError("Failed to estimate alignment transform")

    return cv2.warpAffine(
        image,
        transform,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
