from typing import Any


class CandidateReranker:
    def rerank(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda candidate: (
                float(candidate["distance"]),
                -int(getattr(candidate["template"], "active_face_count", 0)),
                int(getattr(candidate["template"], "outlier_face_count", 0)),
            ),
        )
