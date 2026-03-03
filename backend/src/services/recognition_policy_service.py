from dataclasses import dataclass
from typing import Literal


DEFAULT_MATCH_THRESHOLD = 0.003579
DEFAULT_POSSIBLE_MATCH_THRESHOLD = 0.00665
DEFAULT_MATCH_SEPARATION_MARGIN = 0.000268
DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN = 0.000144


@dataclass(frozen=True)
class RecognitionDecision:
    status: Literal["match", "possible_match", "unknown"]
    confidence: float
    decision_reason: str


class RecognitionPolicyService:
    def evaluate(
        self,
        *,
        best_distance: float,
        second_best_distance: float | None,
        match_threshold: float = DEFAULT_MATCH_THRESHOLD,
        possible_match_threshold: float = DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        match_separation_margin: float = DEFAULT_MATCH_SEPARATION_MARGIN,
        possible_match_separation_margin: float = DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
    ) -> RecognitionDecision:
        possible_match_threshold = max(possible_match_threshold, match_threshold)
        second_gap = (
            float(second_best_distance - best_distance)
            if second_best_distance is not None
            else None
        )

        if best_distance > possible_match_threshold:
            return RecognitionDecision(
                status="unknown",
                confidence=0.0,
                decision_reason="over_possible_threshold",
            )

        if best_distance <= match_threshold:
            if second_gap is None or second_gap >= match_separation_margin:
                return RecognitionDecision(
                    status="match",
                    confidence=self._score_match(best_distance, match_threshold),
                    decision_reason="matched",
                )
            return RecognitionDecision(
                status="possible_match",
                confidence=self._score_possible(
                    best_distance,
                    match_threshold,
                    possible_match_threshold,
                    second_gap=second_gap,
                ),
                decision_reason="possible_match_ambiguous",
            )

        if second_gap is not None and second_gap < possible_match_separation_margin:
            return RecognitionDecision(
                status="possible_match",
                confidence=self._score_possible(
                    best_distance,
                    match_threshold,
                    possible_match_threshold,
                    second_gap=second_gap,
                ),
                decision_reason="possible_match_ambiguous",
            )

        return RecognitionDecision(
            status="possible_match",
            confidence=self._score_possible(
                best_distance,
                match_threshold,
                possible_match_threshold,
                second_gap=second_gap,
            ),
            decision_reason="possible_match_threshold",
        )

    def _score_match(self, distance: float, threshold: float) -> float:
        if threshold <= 0:
            return 0.0

        normalized = max(0.0, min(1.0, 1.0 - (distance / threshold)))
        return float(round(75.0 + (normalized * 25.0), 2))

    def _score_possible(
        self,
        distance: float,
        match_threshold: float,
        possible_match_threshold: float,
        *,
        second_gap: float | None,
    ) -> float:
        if possible_match_threshold <= match_threshold:
            base_score = 55.0
        elif distance <= match_threshold:
            base_score = 70.0
        else:
            normalized = 1.0 - (
                (distance - match_threshold) / max(possible_match_threshold - match_threshold, 1e-6)
            )
            base_score = 42.0 + (max(0.0, min(1.0, normalized)) * 28.0)

        if second_gap is None:
            return float(round(min(base_score + 4.0, 74.0), 2))

        if second_gap < 0.0002:
            base_score -= 8.0
        elif second_gap < 0.0005:
            base_score -= 4.0
        elif second_gap > 0.0015:
            base_score += 3.0

        return float(round(max(35.0, min(base_score, 74.0)), 2))
