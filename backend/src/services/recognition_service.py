from typing import List, Dict, Any
import cv2
import numpy as np

from src.services.ai.pipeline import FaceProcessingPipeline
from src.services.candidate_reranker import CandidateReranker
from src.services.recognition_policy_service import (
    DEFAULT_MATCH_SEPARATION_MARGIN,
    DEFAULT_MATCH_THRESHOLD,
    DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
    DEFAULT_POSSIBLE_MATCH_THRESHOLD,
    RecognitionPolicyService,
)
from src.infrastructure.repositories.face import FaceRepository
from src.infrastructure.repositories.identity_template import IdentityTemplateRepository
from src.infrastructure.repositories.criminal import CriminalRepository
from src.infrastructure.repositories.audit import AuditRepository
from src.domain.models.audit import AuditLog
from src.core.logging import logger


class RecognitionService:
    def __init__(
        self,
        pipeline: FaceProcessingPipeline,
        template_repo: IdentityTemplateRepository,
        face_repo: FaceRepository,
        criminal_repo: CriminalRepository,
        audit_repo: AuditRepository,
        policy_service: RecognitionPolicyService | None = None,
        candidate_reranker: CandidateReranker | None = None,
    ):
        self.pipeline = pipeline
        self.template_repo = template_repo
        self.face_repo = face_repo
        self.criminal_repo = criminal_repo
        self.audit_repo = audit_repo
        self.policy_service = policy_service or RecognitionPolicyService()
        self.candidate_reranker = candidate_reranker or CandidateReranker()

    async def identify_suspects(
        self,
        image_bytes: bytes,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
        possible_match_threshold: float = DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        match_separation_margin: float = DEFAULT_MATCH_SEPARATION_MARGIN,
        possible_match_separation_margin: float = DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
        single_face_only: bool = True,
        include_debug: bool = False,
    ) -> Dict[str, Any]:
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
        detected_face_count = len(processed_faces)
        if single_face_only and processed_faces:
            processed_faces = [self._select_largest_face(processed_faces)]
        
        final_results = []
        debug_faces = []
        
        for face_data in processed_faces:
            embedding = face_data['embedding']
            box = tuple(int(value) for value in face_data['box'])
            area = int(box[2] * box[3])
            
            ranked_candidates = self.candidate_reranker.rerank(
                await self._rank_criminal_candidates(embedding, limit=10)
            )

            if not ranked_candidates:
                decision_reason = "no_candidate_embeddings"
                result = {
                    "box": box,
                    "status": "unknown",
                    "confidence": 0.0,
                    "distance": None,
                    "decision_reason": decision_reason,
                }
                final_results.append(result)
                if include_debug:
                    debug_faces.append({
                        "box": box,
                        "area": area,
                        "selected": True,
                        "decision_reason": decision_reason,
                        "best_distance": None,
                        "second_best_distance": None,
                        "top_candidates": [],
                    })
                continue
                
            best_candidate = ranked_candidates[0]
            distance = float(best_candidate["distance"])
            second_best_other_distance = (
                float(ranked_candidates[1]["distance"]) if len(ranked_candidates) > 1 else None
            )
            decision = self.policy_service.evaluate(
                best_distance=distance,
                second_best_distance=second_best_other_distance,
                match_threshold=threshold,
                possible_match_threshold=possible_match_threshold,
                match_separation_margin=match_separation_margin,
                possible_match_separation_margin=possible_match_separation_margin,
            )

            if decision.status == "unknown":
                debug_top_candidates = []
                if include_debug:
                    debug_top_candidates = await self._enrich_candidates(ranked_candidates[:3])
                result = {
                    "box": box,
                    "status": "unknown",
                    "confidence": 0.0,
                    "distance": distance,
                    "decision_reason": decision.decision_reason,
                }
                final_results.append(result)
                if include_debug:
                    debug_faces.append({
                        "box": box,
                        "area": area,
                        "selected": True,
                        "decision_reason": decision.decision_reason,
                        "best_distance": distance,
                        "second_best_distance": second_best_other_distance,
                        "top_candidates": debug_top_candidates,
                    })
                continue

            best_candidate_data = await self._enrich_candidate(best_candidate)
            if best_candidate_data is None:
                logger.warning(
                    "Recognition candidate referenced missing criminal record: %s",
                    best_candidate["criminal_id"],
                )
                result = {
                    "box": box,
                    "status": "unknown",
                    "confidence": 0.0,
                    "distance": distance,
                    "decision_reason": "missing_criminal_record",
                }
                final_results.append(result)
                if include_debug:
                    debug_faces.append({
                        "box": box,
                        "area": area,
                        "selected": True,
                        "decision_reason": "missing_criminal_record",
                        "best_distance": distance,
                        "second_best_distance": second_best_other_distance,
                        "top_candidates": [],
                    })
                continue

            result = {
                "box": box,
                "status": decision.status,
                "confidence": decision.confidence,
                "distance": distance,
                "decision_reason": decision.decision_reason,
                "criminal": best_candidate_data["criminal"],
            }
            final_results.append(result)
            if include_debug:
                debug_top_candidates = await self._enrich_candidates(ranked_candidates[:3])
                debug_faces.append({
                    "box": box,
                    "area": area,
                    "selected": True,
                    "decision_reason": decision.decision_reason,
                    "best_distance": distance,
                    "second_best_distance": second_best_other_distance,
                    "top_candidates": debug_top_candidates,
                })
            
        # Log the action
        audit_entry = AuditLog(
            action="IDENTIFY",
            details=f"Processed image and found {len([r for r in final_results if r['status'] == 'match'])} matches."
        )
        await self.audit_repo.create(audit_entry)
        
        debug_payload = None
        if include_debug:
            active_embedding_version = getattr(getattr(self.pipeline, "embedder", None), "embedding_version", None)
            debug_payload = {
                "query_embedding_version": active_embedding_version,
                "threshold": threshold,
                "possible_match_threshold": possible_match_threshold,
                "match_separation_margin": match_separation_margin,
                "possible_match_separation_margin": possible_match_separation_margin,
                "single_face_only": single_face_only,
                "detected_face_count": detected_face_count,
                "analyzed_face_count": len(processed_faces),
                "faces": debug_faces,
            }
        
        return {
            "results": final_results,
            "debug": debug_payload,
        }

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

    async def _rank_criminal_candidates(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        matches = await self.template_repo.find_nearest_neighbors(embedding, limit=limit)
        return [
            {
                "criminal_id": str(template.criminal_id),
                "template": template,
                "distance": float(distance),
            }
            for template, distance in matches
        ]

    async def _enrich_candidates(
        self,
        ranked_candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        enriched_candidates: List[Dict[str, Any]] = []
        for candidate in ranked_candidates:
            enriched_candidate = await self._enrich_candidate(candidate)
            if enriched_candidate is not None:
                enriched_candidates.append(enriched_candidate)
        return enriched_candidates

    async def _enrich_candidate(
        self,
        ranked_candidate: Dict[str, Any],
    ) -> Dict[str, Any] | None:
        template = ranked_candidate["template"]
        criminal = await self.criminal_repo.get(template.criminal_id)
        if not criminal:
            return None

        primary_face = None
        if getattr(template, "primary_face_id", None):
            primary_face = await self.face_repo.get(template.primary_face_id)

        return {
            "criminal": {
                "id": ranked_candidate["criminal_id"],
                "name": f"{criminal.first_name} {criminal.last_name}",
                "nic": criminal.nic,
                "threat_level": criminal.threat_level,
            },
            "face_id": str(primary_face.id) if primary_face else "",
            "image_url": primary_face.image_url if primary_face else "",
            "is_primary": bool(primary_face.is_primary) if primary_face else False,
            "embedding_version": template.embedding_version,
            "template_version": template.template_version,
            "active_face_count": template.active_face_count,
            "support_face_count": template.support_face_count,
            "outlier_face_count": template.outlier_face_count,
            "distance": ranked_candidate["distance"],
        }
