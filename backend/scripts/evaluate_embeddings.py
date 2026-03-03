import argparse
import asyncio
import json
import math
import os
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.models.criminal import Criminal  # noqa: E402
from src.domain.models.face import FaceEmbedding  # noqa: E402
from src.domain.models.identity_template import IdentityTemplate  # noqa: E402
from src.services.identity_template_service import IdentityTemplateService  # noqa: E402
from src.services.recognition_policy_service import (  # noqa: E402
    DEFAULT_MATCH_SEPARATION_MARGIN,
    DEFAULT_MATCH_THRESHOLD,
    DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
    DEFAULT_POSSIBLE_MATCH_THRESHOLD,
)


DEFAULT_CURRENT_THRESHOLD = 0.01
DEFAULT_MAX_NEGATIVE_PAIRS = 20000
DEFAULT_MAX_POSITIVE_PAIRS = 10000
DEFAULT_GRID_SIZE = 200


@dataclass(frozen=True)
class EmbeddingRecord:
    face_id: UUID
    criminal_id: UUID
    criminal_name: str
    image_url: str
    embedding_version: str
    is_primary: bool
    embedding: np.ndarray
    created_at: datetime | None = None
    quality_status: str = "accepted"
    template_role: str = "archived"
    template_distance: float | None = None


@dataclass(frozen=True)
class TemplateRecord:
    criminal_id: UUID
    criminal_name: str
    template_version: str
    embedding_version: str
    active_face_count: int
    support_face_count: int
    outlier_face_count: int
    template_embedding: np.ndarray


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate enrolled face embeddings using same-person and different-person distance distributions.",
    )
    parser.add_argument(
        "--embedding-version",
        help="Only evaluate embeddings from a specific embedding_version.",
    )
    parser.add_argument(
        "--max-positive-pairs",
        type=int,
        default=DEFAULT_MAX_POSITIVE_PAIRS,
        help=f"Maximum same-person pairs to evaluate (default: {DEFAULT_MAX_POSITIVE_PAIRS}).",
    )
    parser.add_argument(
        "--max-negative-pairs",
        type=int,
        default=DEFAULT_MAX_NEGATIVE_PAIRS,
        help=f"Maximum different-person pairs to evaluate (default: {DEFAULT_MAX_NEGATIVE_PAIRS}).",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=DEFAULT_GRID_SIZE,
        help=f"Number of thresholds to scan between min/max distances (default: {DEFAULT_GRID_SIZE}).",
    )
    parser.add_argument(
        "--current-threshold",
        type=float,
        default=DEFAULT_CURRENT_THRESHOLD,
        help=f"Current production threshold to score explicitly (default: {DEFAULT_CURRENT_THRESHOLD}).",
    )
    parser.add_argument(
        "--current-match-threshold",
        type=float,
        default=DEFAULT_MATCH_THRESHOLD,
        help=f"Current match threshold for template-policy calibration (default: {DEFAULT_MATCH_THRESHOLD}).",
    )
    parser.add_argument(
        "--current-possible-match-threshold",
        type=float,
        default=DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        help=(
            "Current possible-match threshold for template-policy calibration "
            f"(default: {DEFAULT_POSSIBLE_MATCH_THRESHOLD})."
        ),
    )
    parser.add_argument(
        "--current-match-separation-margin",
        type=float,
        default=DEFAULT_MATCH_SEPARATION_MARGIN,
        help=(
            "Current match separation margin for template-policy calibration "
            f"(default: {DEFAULT_MATCH_SEPARATION_MARGIN})."
        ),
    )
    parser.add_argument(
        "--current-possible-match-separation-margin",
        type=float,
        default=DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
        help=(
            "Current possible-match separation margin for template-policy calibration "
            f"(default: {DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN})."
        ),
    )
    parser.add_argument(
        "--max-template-probes",
        type=int,
        default=5000,
        help="Maximum enrolled faces to evaluate as template probes (default: 5000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampled pair generation.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to save the evaluation report as JSON.",
    )
    return parser


def _load_env_value(name: str) -> str | None:
    direct_value = os.getenv(name)
    if direct_value:
        return direct_value

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        cleaned = value.strip().strip('"').strip("'")
        return cleaned or None
    return None


def build_async_sessionmaker() -> sessionmaker:
    database_url = _load_env_value("DATABASE_URL")
    if not database_url:
        postgres_user = _load_env_value("POSTGRES_USER")
        postgres_password = _load_env_value("POSTGRES_PASSWORD")
        postgres_db = _load_env_value("POSTGRES_DB")
        if postgres_user and postgres_password and postgres_db:
            database_url = (
                f"postgresql+asyncpg://{postgres_user}:{postgres_password}@localhost:5432/{postgres_db}"
            )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set DATABASE_URL directly or provide POSTGRES_USER, "
            "POSTGRES_PASSWORD, and POSTGRES_DB in the repository root .env file."
        )

    engine = create_async_engine(database_url, echo=False, future=True)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def fetch_embedding_records(embedding_version: str | None = None) -> list[EmbeddingRecord]:
    async_session = build_async_sessionmaker()
    async with async_session() as session:
        statement = (
            select(FaceEmbedding, Criminal)
            .join(Criminal, Criminal.id == FaceEmbedding.criminal_id)
            .order_by(FaceEmbedding.created_at)
        )
        if embedding_version:
            statement = statement.where(FaceEmbedding.embedding_version == embedding_version)

        result = await session.execute(statement)
        rows = result.all()

    records: list[EmbeddingRecord] = []
    for face, criminal in rows:
        records.append(
            EmbeddingRecord(
                face_id=face.id,
                criminal_id=face.criminal_id,
                criminal_name=f"{criminal.first_name} {criminal.last_name}",
                image_url=face.image_url,
                embedding_version=face.embedding_version,
                is_primary=bool(face.is_primary),
                created_at=getattr(face, "created_at", None),
                quality_status=getattr(face, "quality_status", "accepted"),
                template_role=getattr(face, "template_role", "archived"),
                template_distance=getattr(face, "template_distance", None),
                embedding=np.asarray(face.embedding, dtype=np.float32),
            )
        )
    return records


async def fetch_template_records(embedding_version: str | None = None) -> list[TemplateRecord]:
    async_session = build_async_sessionmaker()
    async with async_session() as session:
        statement = (
            select(IdentityTemplate, Criminal)
            .join(Criminal, Criminal.id == IdentityTemplate.criminal_id)
            .order_by(IdentityTemplate.updated_at.desc())
        )
        if embedding_version:
            statement = statement.where(IdentityTemplate.embedding_version == embedding_version)

        result = await session.execute(statement)
        rows = result.all()

    records: list[TemplateRecord] = []
    for template, criminal in rows:
        records.append(
            TemplateRecord(
                criminal_id=template.criminal_id,
                criminal_name=f"{criminal.first_name} {criminal.last_name}",
                template_version=template.template_version,
                embedding_version=template.embedding_version,
                active_face_count=template.active_face_count,
                support_face_count=template.support_face_count,
                outlier_face_count=template.outlier_face_count,
                template_embedding=np.asarray(template.template_embedding, dtype=np.float32),
            )
        )
    return records


def summarize_distances(values: np.ndarray) -> dict[str, Any]:
    if values.size == 0:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "median": None,
            "p01": None,
            "p05": None,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "p99": None,
        }

    return {
        "count": int(values.size),
        "min": round(float(np.min(values)), 6),
        "max": round(float(np.max(values)), 6),
        "mean": round(float(np.mean(values)), 6),
        "std": round(float(np.std(values)), 6),
        "median": round(float(np.median(values)), 6),
        "p01": round(float(np.percentile(values, 1)), 6),
        "p05": round(float(np.percentile(values, 5)), 6),
        "p10": round(float(np.percentile(values, 10)), 6),
        "p25": round(float(np.percentile(values, 25)), 6),
        "p75": round(float(np.percentile(values, 75)), 6),
        "p90": round(float(np.percentile(values, 90)), 6),
        "p95": round(float(np.percentile(values, 95)), 6),
        "p99": round(float(np.percentile(values, 99)), 6),
    }


def _pair_distance(left: EmbeddingRecord, right: EmbeddingRecord) -> float:
    return float(np.linalg.norm(left.embedding - right.embedding))


def _normalize_vector(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm <= 0:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


def _vector_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right))


def _record_to_face_model(record: EmbeddingRecord) -> FaceEmbedding:
    return FaceEmbedding(
        id=record.face_id,
        criminal_id=record.criminal_id,
        image_url=record.image_url,
        is_primary=record.is_primary,
        embedding_version=record.embedding_version,
        quality_status=record.quality_status,
        template_role=record.template_role,
        template_distance=record.template_distance,
        created_at=record.created_at or datetime.utcnow(),
        embedding=record.embedding.astype(float).tolist(),
    )


def build_holdout_template_embedding(records: list[EmbeddingRecord]) -> np.ndarray | None:
    if not records:
        return None

    template_builder = IdentityTemplateService(template_repo=None, face_repo=None)
    face_models = [_record_to_face_model(record) for record in records]
    build_result = template_builder._build_template(face_models)
    template_payload = build_result.get("template_payload")
    if template_payload is None:
        return None

    return _normalize_vector(np.asarray(template_payload["template_embedding"], dtype=np.float32))


def evaluate_template_probes(
    records: list[EmbeddingRecord],
    templates: list[TemplateRecord],
    *,
    current_match_threshold: float,
    current_possible_match_threshold: float,
    current_match_separation_margin: float,
    current_possible_match_separation_margin: float,
    max_probes: int,
    rng: random.Random,
    grid_size: int,
) -> dict[str, Any]:
    grouped_records: dict[UUID, list[EmbeddingRecord]] = {}
    for record in records:
        grouped_records.setdefault(record.criminal_id, []).append(record)

    live_templates = {
        template.criminal_id: {
            "criminal_id": template.criminal_id,
            "criminal_name": template.criminal_name,
            "embedding": _normalize_vector(template.template_embedding),
            "template_version": template.template_version,
            "embedding_version": template.embedding_version,
        }
        for template in templates
        if template.template_embedding.size > 0
    }

    eligible_records = [
        record
        for record in records
        if record.criminal_id in grouped_records
        and record.criminal_id in live_templates
        and record.quality_status != "rejected"
        and record.embedding.size > 0
    ]
    total_eligible_probes = len(eligible_records)
    if len(eligible_records) > max_probes:
        eligible_records = rng.sample(eligible_records, max_probes)

    positive_distances: list[float] = []
    negative_distances: list[float] = []
    separation_gaps: list[float] = []
    top1_positive_separation_gaps: list[float] = []
    successful_match_distances: list[float] = []
    ambiguous_match_distances: list[float] = []
    own_rank_counter: Counter[int] = Counter()

    skipped_no_holdout = 0
    own_top1_count = 0
    own_not_top1_count = 0

    for probe in eligible_records:
        holdout_records = [
            record
            for record in grouped_records[probe.criminal_id]
            if record.face_id != probe.face_id and record.quality_status != "rejected" and record.embedding.size > 0
        ]
        if not holdout_records:
            skipped_no_holdout += 1
            continue

        own_template_embedding = build_holdout_template_embedding(holdout_records)
        if own_template_embedding is None:
            skipped_no_holdout += 1
            continue

        candidate_templates = [
            {
                "criminal_id": probe.criminal_id,
                "criminal_name": probe.criminal_name,
                "embedding": own_template_embedding,
                "template_version": "holdout",
                "embedding_version": probe.embedding_version,
            }
        ]
        candidate_templates.extend(
            template
            for criminal_id, template in live_templates.items()
            if criminal_id != probe.criminal_id
        )

        ranked_candidates = sorted(
            (
                {
                    "criminal_id": candidate["criminal_id"],
                    "criminal_name": candidate["criminal_name"],
                    "distance": _vector_distance(probe.embedding, candidate["embedding"]),
                }
                for candidate in candidate_templates
            ),
            key=lambda item: item["distance"],
        )

        own_index = next(
            (index for index, candidate in enumerate(ranked_candidates) if candidate["criminal_id"] == probe.criminal_id),
            None,
        )
        if own_index is None:
            continue

        own_candidate = ranked_candidates[own_index]
        nearest_other_candidate = next(
            (candidate for candidate in ranked_candidates if candidate["criminal_id"] != probe.criminal_id),
            None,
        )
        if nearest_other_candidate is None:
            continue

        own_distance = float(own_candidate["distance"])
        nearest_other_distance = float(nearest_other_candidate["distance"])
        separation_gap = nearest_other_distance - own_distance

        positive_distances.append(own_distance)
        negative_distances.append(nearest_other_distance)
        separation_gaps.append(separation_gap)
        own_rank_counter[own_index + 1] += 1

        if own_index == 0:
            own_top1_count += 1
            top1_positive_separation_gaps.append(separation_gap)
        else:
            own_not_top1_count += 1

        if (
            own_distance <= current_match_threshold
            and separation_gap >= current_match_separation_margin
        ):
            successful_match_distances.append(own_distance)
        elif own_distance <= current_possible_match_threshold:
            ambiguous_match_distances.append(own_distance)

    positive_array = np.asarray(positive_distances, dtype=np.float32)
    negative_array = np.asarray(negative_distances, dtype=np.float32)
    separation_array = np.asarray(separation_gaps, dtype=np.float32)
    top1_positive_gap_array = np.asarray(top1_positive_separation_gaps, dtype=np.float32)
    successful_match_array = np.asarray(successful_match_distances, dtype=np.float32)
    ambiguous_match_array = np.asarray(ambiguous_match_distances, dtype=np.float32)

    threshold_report = evaluate_thresholds(
        positive_array,
        negative_array,
        current_match_threshold,
        grid_size,
    )
    policy_recommendation = recommend_policy_settings(
        threshold_report=threshold_report,
        positive_probe_distances=positive_array,
        separation_gaps=separation_array,
        top1_positive_separation_gaps=top1_positive_gap_array,
        fallback_match_threshold=current_match_threshold,
        fallback_possible_match_threshold=current_possible_match_threshold,
        fallback_match_separation_margin=current_match_separation_margin,
        fallback_possible_match_separation_margin=current_possible_match_separation_margin,
    )

    top1_correct_rate = (
        round(own_top1_count / positive_array.size, 6)
        if positive_array.size
        else None
    )

    return {
        "dataset": {
            "template_count": len(live_templates),
            "total_eligible_probe_faces": total_eligible_probes,
            "evaluated_probe_faces": int(positive_array.size),
            "skipped_no_holdout_faces": skipped_no_holdout,
        },
        "positive_probe_distances": {
            "distance_summary": summarize_distances(positive_array),
        },
        "nearest_other_template_distances": {
            "distance_summary": summarize_distances(negative_array),
        },
        "separation_gaps": {
            "distance_summary": summarize_distances(separation_array),
        },
        "top1_positive_separation_gaps": {
            "distance_summary": summarize_distances(top1_positive_gap_array),
        },
        "current_policy_probe_outcomes": {
            "match_distance_summary": summarize_distances(successful_match_array),
            "possible_match_distance_summary": summarize_distances(ambiguous_match_array),
        },
        "ranking": {
            "own_template_top1_count": own_top1_count,
            "own_template_not_top1_count": own_not_top1_count,
            "own_template_top1_rate": top1_correct_rate,
            "own_template_rank_histogram": {
                str(rank): count for rank, count in sorted(own_rank_counter.items())
            },
        },
        "threshold_report": threshold_report,
        "recommended_policy": policy_recommendation,
    }


def recommend_policy_settings(
    *,
    threshold_report: dict[str, Any],
    positive_probe_distances: np.ndarray,
    separation_gaps: np.ndarray,
    top1_positive_separation_gaps: np.ndarray,
    fallback_match_threshold: float,
    fallback_possible_match_threshold: float,
    fallback_match_separation_margin: float,
    fallback_possible_match_separation_margin: float,
) -> dict[str, Any]:
    recommended = threshold_report.get("recommended", {})
    match_source_label = "far_le_0.010"
    match_source = recommended.get(match_source_label) or recommended.get("best_balanced_accuracy") or {}
    if not match_source:
        match_source_label = "fallback_current_match_threshold"

    match_threshold = float(match_source.get("threshold", fallback_match_threshold))
    positive_probe_summary = summarize_distances(positive_probe_distances)
    positive_probe_p95 = positive_probe_summary.get("p95")
    possible_candidates = [
        (
            "positive_probe_p95",
            {"threshold": positive_probe_p95} if positive_probe_p95 is not None else {},
        ),
        ("best_balanced_accuracy", recommended.get("best_balanced_accuracy") or {}),
        ("far_le_0.100", recommended.get("far_le_0.100") or {}),
        ("far_le_0.050", recommended.get("far_le_0.050") or {}),
        ("far_le_0.010", recommended.get("far_le_0.010") or {}),
    ]
    eligible_possible_candidates = [
        (label, metrics)
        for label, metrics in possible_candidates
        if metrics and float(metrics.get("threshold", 0.0)) >= match_threshold
    ]
    if eligible_possible_candidates:
        possible_source_label, possible_source = max(
            eligible_possible_candidates,
            key=lambda item: float(item[1]["threshold"]),
        )
    else:
        possible_source_label = "fallback_current_possible_match_threshold"
        possible_source = {}

    possible_match_threshold = float(possible_source.get("threshold", fallback_possible_match_threshold))
    possible_match_threshold = max(possible_match_threshold, match_threshold)

    gap_source = top1_positive_separation_gaps if top1_positive_separation_gaps.size else separation_gaps
    gap_summary = summarize_distances(gap_source)
    gap_p10 = gap_summary.get("p10")
    gap_p05 = gap_summary.get("p05")

    match_separation_margin = float(
        gap_p10 if gap_p10 is not None else fallback_match_separation_margin
    )
    possible_match_separation_margin = float(
        gap_p05 if gap_p05 is not None else fallback_possible_match_separation_margin
    )

    match_separation_margin = max(match_separation_margin, 0.0)
    possible_match_separation_margin = max(
        min(possible_match_separation_margin, match_separation_margin),
        0.0,
    )

    return {
        "match_threshold": round(match_threshold, 6),
        "possible_match_threshold": round(possible_match_threshold, 6),
        "match_separation_margin": round(match_separation_margin, 6),
        "possible_match_separation_margin": round(possible_match_separation_margin, 6),
        "match_threshold_source": match_source_label,
        "possible_match_threshold_source": possible_source_label,
        "gap_summary": gap_summary,
        "positive_probe_summary": positive_probe_summary,
    }


def sample_positive_pairs(
    records: list[EmbeddingRecord],
    max_pairs: int,
    rng: random.Random,
) -> tuple[np.ndarray, dict[str, int]]:
    grouped: dict[UUID, list[EmbeddingRecord]] = {}
    for record in records:
        grouped.setdefault(record.criminal_id, []).append(record)

    candidate_pairs: list[tuple[EmbeddingRecord, EmbeddingRecord]] = []
    eligible_identity_count = 0
    total_possible_pairs = 0
    for criminal_records in grouped.values():
        if len(criminal_records) < 2:
            continue
        eligible_identity_count += 1
        total_possible_pairs += math.comb(len(criminal_records), 2)
        for index, left in enumerate(criminal_records):
            for right in criminal_records[index + 1:]:
                candidate_pairs.append((left, right))

    if len(candidate_pairs) > max_pairs:
        candidate_pairs = rng.sample(candidate_pairs, max_pairs)

    distances = np.asarray([_pair_distance(left, right) for left, right in candidate_pairs], dtype=np.float32)
    metadata = {
        "eligible_identity_count": eligible_identity_count,
        "total_possible_pairs": total_possible_pairs,
        "sampled_pairs": int(distances.size),
    }
    return distances, metadata


def sample_negative_pairs(
    records: list[EmbeddingRecord],
    positive_pair_count: int,
    max_pairs: int,
    rng: random.Random,
) -> tuple[np.ndarray, dict[str, int]]:
    total_records = len(records)
    total_pairs = math.comb(total_records, 2) if total_records >= 2 else 0
    total_possible_negative_pairs = max(total_pairs - positive_pair_count, 0)

    if total_records < 2 or total_possible_negative_pairs == 0:
        return np.asarray([], dtype=np.float32), {
            "total_possible_pairs": total_possible_negative_pairs,
            "sampled_pairs": 0,
        }

    if total_possible_negative_pairs <= max_pairs:
        candidate_pairs: list[tuple[EmbeddingRecord, EmbeddingRecord]] = []
        for left_index, left in enumerate(records):
            for right in records[left_index + 1:]:
                if left.criminal_id == right.criminal_id:
                    continue
                candidate_pairs.append((left, right))
    else:
        seen_pairs: set[tuple[int, int]] = set()
        candidate_pairs = []
        max_attempts = max_pairs * 20
        attempts = 0
        while len(candidate_pairs) < max_pairs and attempts < max_attempts:
            left_index, right_index = sorted(rng.sample(range(total_records), 2))
            attempts += 1
            if (left_index, right_index) in seen_pairs:
                continue
            seen_pairs.add((left_index, right_index))

            left = records[left_index]
            right = records[right_index]
            if left.criminal_id == right.criminal_id:
                continue
            candidate_pairs.append((left, right))

    distances = np.asarray([_pair_distance(left, right) for left, right in candidate_pairs], dtype=np.float32)
    metadata = {
        "total_possible_pairs": total_possible_negative_pairs,
        "sampled_pairs": int(distances.size),
    }
    return distances, metadata


def compute_threshold_metrics(
    positive_distances: np.ndarray,
    negative_distances: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    positive_total = int(positive_distances.size)
    negative_total = int(negative_distances.size)

    tp = int(np.sum(positive_distances <= threshold)) if positive_total else 0
    fn = positive_total - tp
    fp = int(np.sum(negative_distances <= threshold)) if negative_total else 0
    tn = negative_total - fp

    tar = (tp / positive_total) if positive_total else None
    frr = (fn / positive_total) if positive_total else None
    far = (fp / negative_total) if negative_total else None
    tnr = (tn / negative_total) if negative_total else None
    precision = (tp / (tp + fp)) if (tp + fp) else None
    balanced_accuracy = (
        ((tar if tar is not None else 0.0) + (tnr if tnr is not None else 0.0)) / 2
        if positive_total and negative_total
        else None
    )

    return {
        "threshold": round(float(threshold), 6),
        "true_accepts": tp,
        "false_rejects": fn,
        "false_accepts": fp,
        "true_rejects": tn,
        "tar": round(float(tar), 6) if tar is not None else None,
        "frr": round(float(frr), 6) if frr is not None else None,
        "far": round(float(far), 6) if far is not None else None,
        "tnr": round(float(tnr), 6) if tnr is not None else None,
        "precision": round(float(precision), 6) if precision is not None else None,
        "balanced_accuracy": round(float(balanced_accuracy), 6) if balanced_accuracy is not None else None,
    }


def evaluate_thresholds(
    positive_distances: np.ndarray,
    negative_distances: np.ndarray,
    current_threshold: float,
    grid_size: int,
) -> dict[str, Any]:
    if positive_distances.size == 0 or negative_distances.size == 0:
        return {
            "current_threshold": compute_threshold_metrics(positive_distances, negative_distances, current_threshold),
            "scanned_threshold_count": 0,
            "recommended": {},
        }

    lower_bound = float(min(np.min(positive_distances), np.min(negative_distances)))
    upper_bound = float(max(np.max(positive_distances), np.max(negative_distances)))
    candidate_thresholds = np.linspace(lower_bound, upper_bound, num=max(grid_size, 2))

    metrics = [
        compute_threshold_metrics(positive_distances, negative_distances, threshold)
        for threshold in candidate_thresholds
    ]

    best_balanced = max(
        metrics,
        key=lambda item: item["balanced_accuracy"] if item["balanced_accuracy"] is not None else float("-inf"),
    )

    far_targets = [0.001, 0.01, 0.05, 0.1]
    far_recommendations: dict[str, dict[str, Any]] = {}
    for target in far_targets:
        eligible = [item for item in metrics if item["far"] is not None and item["far"] <= target]
        if not eligible:
            far_recommendations[f"far_le_{target:.3f}"] = {}
            continue
        chosen = max(
            eligible,
            key=lambda item: (
                item["tar"] if item["tar"] is not None else float("-inf"),
                -(item["threshold"]),
            ),
        )
        far_recommendations[f"far_le_{target:.3f}"] = chosen

    return {
        "current_threshold": compute_threshold_metrics(positive_distances, negative_distances, current_threshold),
        "scanned_threshold_count": len(metrics),
        "recommended": {
            "best_balanced_accuracy": best_balanced,
            **far_recommendations,
        },
    }


def build_report(
    records: list[EmbeddingRecord],
    positive_distances: np.ndarray,
    positive_metadata: dict[str, int],
    negative_distances: np.ndarray,
    negative_metadata: dict[str, int],
    threshold_report: dict[str, Any],
    template_calibration: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    criminal_counts: dict[UUID, int] = {}
    embedding_versions: dict[str, int] = {}
    for record in records:
        criminal_counts[record.criminal_id] = criminal_counts.get(record.criminal_id, 0) + 1
        embedding_versions[record.embedding_version] = embedding_versions.get(record.embedding_version, 0) + 1

    positive_summary = summarize_distances(positive_distances)
    negative_summary = summarize_distances(negative_distances)

    overlap_ratio = None
    if positive_distances.size and negative_distances.size:
        overlap_ratio = round(
            float(np.mean(negative_distances <= np.max(positive_distances))),
            6,
        )

    return {
        "configuration": {
            "embedding_version": args.embedding_version,
            "max_positive_pairs": args.max_positive_pairs,
            "max_negative_pairs": args.max_negative_pairs,
            "grid_size": args.grid_size,
            "current_threshold": args.current_threshold,
            "current_match_threshold": args.current_match_threshold,
            "current_possible_match_threshold": args.current_possible_match_threshold,
            "current_match_separation_margin": args.current_match_separation_margin,
            "current_possible_match_separation_margin": args.current_possible_match_separation_margin,
            "max_template_probes": args.max_template_probes,
            "seed": args.seed,
        },
        "dataset": {
            "face_count": len(records),
            "criminal_count": len(criminal_counts),
            "criminals_with_multiple_faces": positive_metadata["eligible_identity_count"],
            "embedding_versions": embedding_versions,
        },
        "positive_pairs": {
            "metadata": positive_metadata,
            "distance_summary": positive_summary,
        },
        "negative_pairs": {
            "metadata": negative_metadata,
            "distance_summary": negative_summary,
        },
        "separation": {
            "positive_p95": positive_summary["p95"],
            "negative_p05": negative_summary["p05"],
            "estimated_overlap_ratio": overlap_ratio,
        },
        "threshold_report": threshold_report,
        "template_calibration": template_calibration,
    }


def print_report(report: dict[str, Any]) -> None:
    dataset = report["dataset"]
    positive_summary = report["positive_pairs"]["distance_summary"]
    negative_summary = report["negative_pairs"]["distance_summary"]
    separation = report["separation"]
    threshold_report = report["threshold_report"]
    template_calibration = report["template_calibration"]
    template_dataset = template_calibration["dataset"]
    template_positive = template_calibration["positive_probe_distances"]["distance_summary"]
    template_negative = template_calibration["nearest_other_template_distances"]["distance_summary"]
    template_gaps = template_calibration["separation_gaps"]["distance_summary"]
    template_top1_gaps = template_calibration["top1_positive_separation_gaps"]["distance_summary"]
    ranking = template_calibration["ranking"]
    recommended_policy = template_calibration["recommended_policy"]

    print("\nEmbedding Evaluation Report")
    print("=" * 28)
    print(
        f"Faces: {dataset['face_count']} across {dataset['criminal_count']} criminals "
        f"({dataset['criminals_with_multiple_faces']} with >=2 enrolled faces)"
    )
    print(f"Embedding versions: {dataset['embedding_versions']}")

    print("\nPositive pair distances (same criminal)")
    print("-------------------------------------")
    print(
        f"Pairs: {positive_summary['count']} | "
        f"mean={positive_summary['mean']} median={positive_summary['median']} "
        f"p95={positive_summary['p95']} max={positive_summary['max']}"
    )

    print("\nNegative pair distances (different criminals)")
    print("---------------------------------------------")
    print(
        f"Pairs: {negative_summary['count']} | "
        f"mean={negative_summary['mean']} median={negative_summary['median']} "
        f"p05={negative_summary['p05']} min={negative_summary['min']}"
    )

    print("\nSeparation summary")
    print("------------------")
    print(
        f"positive_p95={separation['positive_p95']} | "
        f"negative_p05={separation['negative_p05']} | "
        f"estimated_overlap_ratio={separation['estimated_overlap_ratio']}"
    )

    current = threshold_report["current_threshold"]
    print("\nCurrent threshold")
    print("-----------------")
    print(
        f"threshold={current['threshold']} | "
        f"TAR={current['tar']} FAR={current['far']} FRR={current['frr']} "
        f"precision={current['precision']} balanced_accuracy={current['balanced_accuracy']}"
    )

    print("\nRecommended thresholds")
    print("----------------------")
    for label, metrics in threshold_report["recommended"].items():
        if not metrics:
            print(f"{label}: no threshold met this target with current sample")
            continue
        print(
            f"{label}: threshold={metrics['threshold']} TAR={metrics['tar']} FAR={metrics['far']} "
            f"precision={metrics['precision']} balanced_accuracy={metrics['balanced_accuracy']}"
        )

    print("\nTemplate calibration")
    print("--------------------")
    print(
        f"Templates: {template_dataset['template_count']} | "
        f"eligible_probe_faces={template_dataset['total_eligible_probe_faces']} | "
        f"evaluated_probe_faces={template_dataset['evaluated_probe_faces']} | "
        f"skipped_no_holdout_faces={template_dataset['skipped_no_holdout_faces']}"
    )
    print(
        f"positive_probe_p95={template_positive['p95']} | "
        f"nearest_other_p05={template_negative['p05']} | "
        f"gap_p10={template_gaps['p10']} | "
        f"top1_gap_p10={template_top1_gaps['p10']} | "
        f"own_template_top1_rate={ranking['own_template_top1_rate']}"
    )

    template_current = template_calibration["threshold_report"]["current_threshold"]
    print("\nCurrent template match threshold")
    print("-------------------------------")
    print(
        f"threshold={template_current['threshold']} | "
        f"TAR={template_current['tar']} FAR={template_current['far']} FRR={template_current['frr']} "
        f"precision={template_current['precision']} balanced_accuracy={template_current['balanced_accuracy']}"
    )

    print("\nRecommended recognition policy")
    print("------------------------------")
    print(
        f"match_threshold={recommended_policy['match_threshold']} "
        f"({recommended_policy['match_threshold_source']}) | "
        f"possible_match_threshold={recommended_policy['possible_match_threshold']} "
        f"({recommended_policy['possible_match_threshold_source']})"
    )
    print(
        f"match_separation_margin={recommended_policy['match_separation_margin']} | "
        f"possible_match_separation_margin={recommended_policy['possible_match_separation_margin']}"
    )
    print()


async def async_main(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    records = await fetch_embedding_records(args.embedding_version)
    templates = await fetch_template_records(args.embedding_version)
    if len(records) < 2:
        print("Not enough enrolled face embeddings to evaluate. Need at least 2 records.")
        return 1
    if not templates:
        print("No identity templates found. Build templates before running evaluation.")
        return 1

    positive_distances, positive_metadata = sample_positive_pairs(records, args.max_positive_pairs, rng)
    negative_distances, negative_metadata = sample_negative_pairs(
        records,
        positive_metadata["total_possible_pairs"],
        args.max_negative_pairs,
        rng,
    )

    threshold_report = evaluate_thresholds(
        positive_distances,
        negative_distances,
        args.current_threshold,
        args.grid_size,
    )
    template_calibration = evaluate_template_probes(
        records,
        templates,
        current_match_threshold=args.current_match_threshold,
        current_possible_match_threshold=args.current_possible_match_threshold,
        current_match_separation_margin=args.current_match_separation_margin,
        current_possible_match_separation_margin=args.current_possible_match_separation_margin,
        max_probes=args.max_template_probes,
        rng=rng,
        grid_size=args.grid_size,
    )
    report = build_report(
        records,
        positive_distances,
        positive_metadata,
        negative_distances,
        negative_metadata,
        threshold_report,
        template_calibration,
        args,
    )

    print_report(report)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved JSON report to {args.output_json}")

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
