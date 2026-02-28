from typing import List, Dict, Any
import cv2
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ai.pipeline import FaceProcessingPipeline
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.audit import AuditRepository
from src.domain.models.audit import AuditLog
from src.core.logging import logger


DEFAULT_MATCH_THRESHOLD = 0.45
DEFAULT_AMBIGUITY_MARGIN = 0.08


class RecognitionService:
    def __init__(
        self,
        pipeline: FaceProcessingPipeline,
        face_repo: FaceRepository,
        criminal_repo: CriminalRepository,
        audit_repo: AuditRepository
    ):
        self.pipeline = pipeline
        self.face_repo = face_repo
        self.criminal_repo = criminal_repo
        self.audit_repo = audit_repo

    async def identify_suspects(
        self,
        image_bytes: bytes,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
        ambiguity_margin: float = DEFAULT_AMBIGUITY_MARGIN,
        single_face_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        End-to-end identification flow.
        1. Process image via AI Pipeline.
        2. Query Vector DB for matches.
        3. Enrich with Criminal Profile data.
        """
        # Convert bytes to numpy
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_np is None:
            raise ValueError("Invalid image data")
        
        # Convert BGR to RGB (OpenCV default is BGR, AI usually expects RGB or handles it)
        img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        
        processed_faces = self.pipeline.process_image(img_rgb)
        if single_face_only and processed_faces:
            processed_faces = [self._select_largest_face(processed_faces)]
        
        final_results = []
        
        for face_data in processed_faces:
            embedding = face_data['embedding']
            box = face_data['box']
            
            # Vector Search
            matches = await self.face_repo.find_nearest_neighbors(embedding, limit=5)
            
            if not matches:
                final_results.append({
                    "box": box,
                    "status": "unknown",
                    "confidence": 0.0
                })
                continue
                
            best_match_face, distance = matches[0]
            second_best_other_distance = self._get_second_best_other_criminal_distance(
                matches,
                best_match_face.criminal_id,
            )
            
            # Convert L2 distance to Confidence Score using calibrated Sigmoid function
            # FaceNet Euclidean distances: < 0.6 is a strong match, > 0.9 is weak.
            # This sigmoid centers around 0.65 mapping distance to a 0-100% curve.
            confidence_float = 100.0 / (1.0 + np.exp(10.0 * (distance - 0.65)))
            confidence = float(confidence_float)
            
            if distance > threshold:
                final_results.append({
                    "box": box,
                    "status": "unknown",
                    "confidence": 0.0,
                })
                continue

            if (
                second_best_other_distance is not None
                and (second_best_other_distance - distance) < ambiguity_margin
            ):
                logger.info(
                    "Rejected ambiguous recognition candidate. best_distance=%.4f second_best_distance=%.4f",
                    distance,
                    second_best_other_distance,
                )
                final_results.append({
                    "box": box,
                    "status": "unknown",
                    "confidence": 0.0,
                })
                continue
                
            # Fetch Profile
            criminal = await self.criminal_repo.get(best_match_face.criminal_id)
            
            final_results.append({
                "box": box,
                "status": "match",
                "confidence": confidence,
                "criminal": {
                    "id": str(criminal.id),
                    "name": f"{criminal.first_name} {criminal.last_name}",
                    "nic": criminal.nic,
                    "threat_level": criminal.threat_level
                }
            })
            
        # Log the action
        audit_entry = AuditLog(
            action="IDENTIFY",
            details=f"Processed image and found {len([r for r in final_results if r['status'] == 'match'])} matches."
        )
        await self.audit_repo.create(audit_entry)
        
        return final_results

    def _select_largest_face(self, processed_faces: List[Dict[str, Any]]) -> Dict[str, Any]:
        return max(processed_faces, key=lambda face: face["box"][2] * face["box"][3])

    def _get_second_best_other_criminal_distance(
        self,
        matches: List[Any],
        best_criminal_id: Any,
    ) -> float | None:
        for face_match, distance in matches[1:]:
            if face_match.criminal_id != best_criminal_id:
                return float(distance)
        return None
