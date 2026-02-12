from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np

class FaceDetectionStrategy(ABC):
    @abstractmethod
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detects faces in an image.
        Returns a list of bounding boxes (x, y, w, h).
        """
        pass

class FaceEmbeddingStrategy(ABC):
    @abstractmethod
    def embed_face(self, face_image: np.ndarray) -> List[float]:
        """
        Generates a vector embedding for a single aligned face image.
        Returns a 512-dimensional list of floats.
        """
        pass
