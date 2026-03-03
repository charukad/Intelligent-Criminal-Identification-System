import numpy as np

from src.services.ai.pipeline import FaceProcessingPipeline


class DetectorWithLandmarks:
    def detect_faces_with_landmarks(self, _image):
        return [
            {
                "box": (10, 20, 60, 70),
                "landmarks": [
                    (30.0, 45.0),
                    (60.0, 42.0),
                    (45.0, 58.0),
                    (34.0, 74.0),
                    (58.0, 71.0),
                ],
            }
        ]


class DetectorWithoutLandmarks:
    def detect_faces(self, _image):
        return [(10, 20, 60, 70)]


class RecordingEmbedder:
    def __init__(self):
        self.last_shape = None

    def embed_face(self, face_image):
        self.last_shape = face_image.shape
        return [0.1, 0.2, 0.3]


def test_pipeline_aligns_faces_when_landmarks_are_available():
    image = np.zeros((160, 160, 3), dtype=np.uint8)
    embedder = RecordingEmbedder()
    pipeline = FaceProcessingPipeline(DetectorWithLandmarks(), embedder)

    results = pipeline.process_image(image)

    assert len(results) == 1
    assert embedder.last_shape == (112, 112, 3)


def test_pipeline_falls_back_to_raw_crop_without_landmarks():
    image = np.zeros((160, 160, 3), dtype=np.uint8)
    embedder = RecordingEmbedder()
    pipeline = FaceProcessingPipeline(DetectorWithoutLandmarks(), embedder)

    results = pipeline.process_image(image)

    assert len(results) == 1
    assert embedder.last_shape == (70, 60, 3)
