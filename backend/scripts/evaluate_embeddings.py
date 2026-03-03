import argparse
import asyncio
import json
import math
import os
import random
from dataclasses import dataclass
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
                embedding=np.asarray(face.embedding, dtype=np.float32),
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

    far_targets = [0.001, 0.01, 0.05]
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
    }


def print_report(report: dict[str, Any]) -> None:
    dataset = report["dataset"]
    positive_summary = report["positive_pairs"]["distance_summary"]
    negative_summary = report["negative_pairs"]["distance_summary"]
    separation = report["separation"]
    threshold_report = report["threshold_report"]

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
    print()


async def async_main(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    records = await fetch_embedding_records(args.embedding_version)
    if len(records) < 2:
        print("Not enough enrolled face embeddings to evaluate. Need at least 2 records.")
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
    report = build_report(
        records,
        positive_distances,
        positive_metadata,
        negative_distances,
        negative_metadata,
        threshold_report,
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
