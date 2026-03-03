import numpy as np
from typing import List, Dict, Any, Tuple

from src.services.ai.face_alignment import align_face_to_template
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
        face_regions = self.extract_face_regions(image)
        logger.info(f"Detected {len(face_regions)} usable faces.")

        results = []
        for face_region in face_regions:
            try:
                embedding = self.embedder.embed_face(face_region["crop"])
                results.append({
                    "box": face_region["box"],
                    "embedding": embedding,
                    "landmarks": face_region.get("landmarks"),
                    "alignment_applied": bool(face_region.get("alignment_applied")),
                })
            except Exception as e:
                x, y, _w, _h = face_region["box"]
                logger.error(f"Failed to embed face at {x},{y}: {e}")

        return results

    def extract_face_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces and return usable cropped regions before embedding.
        Returns a list of dicts: {'box': (x,y,w,h), 'crop': np.ndarray}
        """
        logger.info("Extracting face regions from image...")
        detections = self._detect_face_detections(image)
        logger.info(f"Detector found {len(detections)} raw faces.")

        results: List[Dict[str, Any]] = []
        h_img, w_img, _ = image.shape
        for detection in detections:
            x, y, w, h = detection["box"]
            if w < 20 or h < 20:
                continue

            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w_img, x + w), min(h_img, y + h)
            face_crop = image[y1:y2, x1:x2]
            if face_crop.size == 0:
                continue

            aligned_crop = face_crop
            alignment_applied = False
            landmarks = detection.get("landmarks")
            if landmarks:
                try:
                    aligned_crop = align_face_to_template(image, landmarks)
                    alignment_applied = True
                except Exception as exc:
                    logger.warning("Face alignment failed for box %s: %s", detection["box"], exc)

            results.append({
                "box": detection["box"],
                "crop": aligned_crop,
                "raw_crop": face_crop,
                "landmarks": landmarks,
                "alignment_applied": alignment_applied,
            })

        return results

    def _detect_face_detections(self, image: np.ndarray) -> List[Dict[str, Any]]:
        detector_with_landmarks = getattr(self.detector, "detect_faces_with_landmarks", None)
        if callable(detector_with_landmarks):
            return detector_with_landmarks(image)

        return [
            {
                "box": box,
                "landmarks": None,
            }
            for box in self.detector.detect_faces(image)
        ]
