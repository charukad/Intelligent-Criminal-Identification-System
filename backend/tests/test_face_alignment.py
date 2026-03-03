import numpy as np

from src.services.ai.face_alignment import REFERENCE_5PTS, align_face_to_template


def test_align_face_to_template_maps_landmarks_to_reference_region():
    image = np.zeros((140, 140, 3), dtype=np.uint8)
    colors = [
        np.array([255, 0, 0], dtype=np.uint8),
        np.array([0, 255, 0], dtype=np.uint8),
        np.array([0, 0, 255], dtype=np.uint8),
        np.array([255, 255, 0], dtype=np.uint8),
        np.array([255, 0, 255], dtype=np.uint8),
    ]
    source_landmarks = np.asarray(
        [
            [28.0, 52.0],
            [92.0, 48.0],
            [60.0, 76.0],
            [36.0, 98.0],
            [84.0, 94.0],
        ],
        dtype=np.float32,
    )

    for point, color in zip(source_landmarks.astype(int), colors):
        x, y = point
        image[y - 4:y + 5, x - 4:x + 5] = color

    aligned = align_face_to_template(image, source_landmarks)

    assert aligned.shape == (112, 112, 3)
    for reference_point, color in zip(REFERENCE_5PTS.astype(int), colors):
        x, y = reference_point
        patch = aligned[max(0, y - 5):y + 6, max(0, x - 5):x + 6]
        assert patch.size > 0
        dominant_channel = int(np.argmax(color))
        dominant_energy = float(patch[:, :, dominant_channel].sum())
        other_channels = [channel for channel in range(3) if channel != dominant_channel]
        other_energy = float(patch[:, :, other_channels].sum())
        assert dominant_energy > 0
        assert dominant_energy >= other_energy / max(len(other_channels), 1)
