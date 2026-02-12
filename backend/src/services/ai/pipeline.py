import numpy as np
from typing import List, Dict, Any, Tuple

from src.services.ai.interfaces import FaceDetectionStrategy, FaceEmbeddingStrategy
from src.core.logging import logger

class FaceProcessingPipeline:
    def __init__(
        self, 
        detector: FaceDetectionStrategy, 
        embedder: FaceEmbeddingStrategy
    ):
        self.detector = detector
        self.embedder = embedder

    def process_image(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Full pipeline: Detect -> Crop -> Embed.
        Returns a list of dicts: {'box': (x,y,w,h), 'embedding': [...]}
        """
        logger.info("Starting Face Processing Pipeline...")
        faces_param = self.detector.detect_faces(image)
        logger.info(f"Detected {len(faces_param)} faces.")
        
        results = []
        for (x, y, w, h) in faces_param:
            # Basic sanity check
            if w < 20 or h < 20: 
                continue

            # Safe crop with boundary checks
            h_img, w_img, _ = image.shape
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w_img, x + w), min(h_img, y + h)
            
            face_crop = image[y1:y2, x1:x2]
            
            try:
                embedding = self.embedder.embed_face(face_crop)
                results.append({
                    "box": (x, y, w, h),
                    "embedding": embedding
                })
            except Exception as e:
                logger.error(f"Failed to embed face at {x},{y}: {e}")
                
        return results
