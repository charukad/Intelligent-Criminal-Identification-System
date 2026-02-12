from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ai.pipeline import FaceProcessingPipeline
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.core.logging import logger

class RecognitionService:
    def __init__(
        self,
        pipeline: FaceProcessingPipeline,
        face_repo: FaceRepository,
        criminal_repo: CriminalRepository
    ):
        self.pipeline = pipeline
        self.face_repo = face_repo
        self.criminal_repo = criminal_repo

    async def identify_suspects(self, image_bytes: bytes, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        End-to-end identification flow.
        1. Process image via AI Pipeline.
        2. Query Vector DB for matches.
        3. Enrich with Criminal Profile data.
        """
        # Convert bytes to numpy (Need opencv or numpy decode)
        import cv2
        import numpy as np
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert BGR to RGB (OpenCV default is BGR, AI usually expects RGB or handles it)
        img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        
        processed_faces = self.pipeline.process_image(img_rgb)
        
        final_results = []
        
        for face_data in processed_faces:
            embedding = face_data['embedding']
            box = face_data['box']
            
            # Vector Search
            # limit=1 means we just want the TOP match for this specific face
            matches = await self.face_repo.find_nearest_neighbors(embedding, limit=1)
            
            if not matches:
                continue
                
            best_match_face, distance = matches[0]
            
            # Convert L2 distance to Confidence Score (Inverse relationship)
            # Thresholding logic: (Euclidean distance for FaceNet is roughly 0 to <1.5)
            # Heuristic: confidence = max(0, (1 - distance / 2.0)) * 100
            # Note: This is arbitrary and needs tuning.
            confidence = max(0.0, (1.2 - distance) / 1.2) * 100
            
            if distance > threshold:
                # No match found within threshold
                final_results.append({
                    "box": box,
                    "status": "unknown",
                    "confidence": confidence # Low
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
            
        return final_results
