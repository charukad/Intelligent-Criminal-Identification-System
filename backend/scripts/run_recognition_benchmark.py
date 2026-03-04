import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid5, NAMESPACE_URL

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_embeddings import (  # noqa: E402
    EmbeddingRecord,
    TemplateRecord,
    DEFAULT_CURRENT_THRESHOLD,
    build_holdout_template_embedding,
    evaluate_template_probes,
    evaluate_thresholds,
    summarize_distances,
)
from src.services.ai.strategies import DEFAULT_EMBEDDING_VERSION, normalize_embedding_version  # noqa: E402
from src.services.recognition_policy_service import (  # noqa: E402
    DEFAULT_MATCH_SEPARATION_MARGIN,
    DEFAULT_MATCH_THRESHOLD,
    DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
    DEFAULT_POSSIBLE_MATCH_THRESHOLD,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an offline face-recognition benchmark from a benchmark manifest.",
    )
    parser.add_argument("manifest", type=Path, help="Path to the benchmark manifest JSON.")
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to save the benchmark report JSON. Defaults under backend/uploads/benchmarks.",
    )
    parser.add_argument(
        "--current-threshold",
        type=float,
        default=DEFAULT_CURRENT_THRESHOLD,
        help=f"Current pair threshold to score explicitly (default: {DEFAULT_CURRENT_THRESHOLD}).",
    )
    parser.add_argument(
        "--current-match-threshold",
        type=float,
        default=DEFAULT_MATCH_THRESHOLD,
        help=f"Current match threshold (default: {DEFAULT_MATCH_THRESHOLD}).",
    )
    parser.add_argument(
        "--current-possible-match-threshold",
        type=float,
        default=DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        help=f"Current possible-match threshold (default: {DEFAULT_POSSIBLE_MATCH_THRESHOLD}).",
    )
    parser.add_argument(
        "--current-match-separation-margin",
        type=float,
        default=DEFAULT_MATCH_SEPARATION_MARGIN,
        help=f"Current match separation margin (default: {DEFAULT_MATCH_SEPARATION_MARGIN}).",
    )
    parser.add_argument(
        "--current-possible-match-separation-margin",
        type=float,
        default=DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
        help=(
            "Current possible-match separation margin "
            f"(default: {DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN})."
        ),
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=200,
        help="Threshold scan size for pair metrics (default: 200).",
    )
    parser.add_argument(
        "--embedding-version",
        default=DEFAULT_EMBEDDING_VERSION,
        help=(
            "Embedding version to evaluate "
            f"(default: {DEFAULT_EMBEDDING_VERSION})."
        ),
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help=(
            "Optional custom checkpoint path. "
            "Use this when evaluating a new TraceNet checkpoint under a custom version label."
        ),
    )
    return parser


def _default_output_path(dataset_name: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_name = dataset_name.replace(" ", "-").lower()
    return PROJECT_ROOT / "uploads" / "benchmarks" / f"{safe_name}-{timestamp}.json"


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def decode_rgb_image(image_path: Path) -> np.ndarray:
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise ValueError(f"Unable to decode image: {image_path}")
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def build_embedding_records(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
    embedding_version: str = DEFAULT_EMBEDDING_VERSION,
    model_path: Path | None = None,
    face_pipeline: Any | None = None,
) -> tuple[list[EmbeddingRecord], list[dict[str, Any]]]:
    dataset_root = Path(manifest["dataset"]["dataset_root"])
    records: list[EmbeddingRecord] = []
    failures: list[dict[str, Any]] = []
    resolved_embedding_version = normalize_embedding_version(embedding_version)
    resolved_pipeline = face_pipeline
    if resolved_pipeline is None:
        from src.services.ai.runtime import get_pipeline  # noqa: E402

        resolved_pipeline = get_pipeline(
            resolved_embedding_version,
            model_path=model_path,
        )

    for image_entry in manifest.get("images", []):
        image_path = dataset_root / image_entry["path"]
        try:
            image = decode_rgb_image(image_path)
            processed_faces = resolved_pipeline.process_image(image)
            if not processed_faces:
                raise ValueError("no_face_detected")
            if len(processed_faces) != 1:
                raise ValueError(f"expected_single_face_detected:{len(processed_faces)}")

            face = processed_faces[0]
            embedding = np.asarray(face["embedding"], dtype=np.float32)
            records.append(
                EmbeddingRecord(
                    face_id=uuid5(NAMESPACE_URL, image_entry["image_id"]),
                    criminal_id=uuid5(NAMESPACE_URL, image_entry["identity"]),
                    criminal_name=image_entry["identity"],
                    image_url=image_entry["path"],
                    embedding_version=resolved_embedding_version,
                    is_primary=False,
                    embedding=embedding,
                    created_at=datetime.now(timezone.utc),
                    quality_status="accepted",
                    template_role="archived",
                    template_distance=None,
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "image_id": image_entry["image_id"],
                    "identity": image_entry["identity"],
                    "path": str(image_path if image_path.is_absolute() else (manifest_path.parent / image_path)),
                    "reason": str(exc),
                }
            )

    return records, failures


def compute_manifest_pair_distances(
    manifest: dict[str, Any],
    *,
    records: list[EmbeddingRecord],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    record_by_image_id = {record.image_url: record for record in records}
    manifest_image_path_by_id = {
        image_entry["image_id"]: image_entry["path"]
        for image_entry in manifest.get("images", [])
    }

    positive_distances: list[float] = []
    negative_distances: list[float] = []
    missing_pairs: list[dict[str, Any]] = []

    for pair in manifest.get("pairs", {}).get("positive", []):
        left = record_by_image_id.get(manifest_image_path_by_id.get(pair["left_image_id"], ""))
        right = record_by_image_id.get(manifest_image_path_by_id.get(pair["right_image_id"], ""))
        if left is None or right is None:
            missing_pairs.append({"pair_id": pair["pair_id"], "label": pair["label"]})
            continue
        positive_distances.append(float(np.linalg.norm(left.embedding - right.embedding)))

    for pair in manifest.get("pairs", {}).get("negative", []):
        left = record_by_image_id.get(manifest_image_path_by_id.get(pair["left_image_id"], ""))
        right = record_by_image_id.get(manifest_image_path_by_id.get(pair["right_image_id"], ""))
        if left is None or right is None:
            missing_pairs.append({"pair_id": pair["pair_id"], "label": pair["label"]})
            continue
        negative_distances.append(float(np.linalg.norm(left.embedding - right.embedding)))

    metadata = {
        "requested_positive_pairs": len(manifest.get("pairs", {}).get("positive", [])),
        "requested_negative_pairs": len(manifest.get("pairs", {}).get("negative", [])),
        "evaluated_positive_pairs": len(positive_distances),
        "evaluated_negative_pairs": len(negative_distances),
        "missing_pairs": missing_pairs,
    }
    return (
        np.asarray(positive_distances, dtype=np.float32),
        np.asarray(negative_distances, dtype=np.float32),
        metadata,
    )


def build_template_records(records: list[EmbeddingRecord]) -> list[TemplateRecord]:
    grouped_records: dict[Any, list[EmbeddingRecord]] = defaultdict(list)
    for record in records:
        grouped_records[record.criminal_id].append(record)

    templates: list[TemplateRecord] = []
    for criminal_id, criminal_records in grouped_records.items():
        template_embedding = build_holdout_template_embedding(criminal_records)
        if template_embedding is None:
            continue
        templates.append(
            TemplateRecord(
                criminal_id=criminal_id,
                criminal_name=criminal_records[0].criminal_name,
                template_version="benchmark_template_v1",
                embedding_version=criminal_records[0].embedding_version,
                active_face_count=len(criminal_records),
                support_face_count=max(len(criminal_records) - 1, 0),
                outlier_face_count=0,
                template_embedding=template_embedding,
            )
        )
    return templates


def build_benchmark_report(
    *,
    manifest: dict[str, Any],
    records: list[EmbeddingRecord],
    failures: list[dict[str, Any]],
    positive_distances: np.ndarray,
    negative_distances: np.ndarray,
    pair_metadata: dict[str, Any],
    threshold_report: dict[str, Any],
    template_calibration: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    image_failures_by_reason: dict[str, int] = defaultdict(int)
    for failure in failures:
        image_failures_by_reason[failure["reason"]] += 1

    return {
        "report_type": "recognition_benchmark",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            **manifest["dataset"],
            "evaluated_image_count": len(records),
            "failed_image_count": len(failures),
        },
        "configuration": {
            "manifest_path": str(args.manifest.resolve()),
            "embedding_version": normalize_embedding_version(args.embedding_version),
            "model_path": str(args.model_path.resolve()) if args.model_path else None,
            "current_threshold": args.current_threshold,
            "current_match_threshold": args.current_match_threshold,
            "current_possible_match_threshold": args.current_possible_match_threshold,
            "current_match_separation_margin": args.current_match_separation_margin,
            "current_possible_match_separation_margin": args.current_possible_match_separation_margin,
            "grid_size": args.grid_size,
        },
        "image_failures": {
            "count_by_reason": dict(sorted(image_failures_by_reason.items())),
            "items": failures,
        },
        "pair_evaluation": {
            "metadata": pair_metadata,
            "positive_pairs": {
                "distance_summary": summarize_distances(positive_distances),
            },
            "negative_pairs": {
                "distance_summary": summarize_distances(negative_distances),
            },
            "separation": {
                "positive_p95": summarize_distances(positive_distances)["p95"],
                "negative_p05": summarize_distances(negative_distances)["p05"],
            },
            "threshold_report": threshold_report,
        },
        "template_calibration": template_calibration,
    }


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_manifest(args.manifest)
    records, failures = build_embedding_records(
        manifest,
        manifest_path=args.manifest,
        embedding_version=args.embedding_version,
        model_path=args.model_path,
    )
    if len(records) < 2:
        raise SystemExit("Not enough benchmark images produced usable embeddings.")

    positive_distances, negative_distances, pair_metadata = compute_manifest_pair_distances(
        manifest,
        records=records,
    )
    threshold_report = evaluate_thresholds(
        positive_distances,
        negative_distances,
        args.current_threshold,
        args.grid_size,
    )

    templates = build_template_records(records)
    template_calibration = evaluate_template_probes(
        records,
        templates,
        current_match_threshold=args.current_match_threshold,
        current_possible_match_threshold=args.current_possible_match_threshold,
        current_match_separation_margin=args.current_match_separation_margin,
        current_possible_match_separation_margin=args.current_possible_match_separation_margin,
        max_probes=len(records),
        rng=__import__("random").Random(manifest["dataset"].get("seed", 42)),
        grid_size=args.grid_size,
    )

    report = build_benchmark_report(
        manifest=manifest,
        records=records,
        failures=failures,
        positive_distances=positive_distances,
        negative_distances=negative_distances,
        pair_metadata=pair_metadata,
        threshold_report=threshold_report,
        template_calibration=template_calibration,
        args=args,
    )
    return report


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    report = run_benchmark(args)
    manifest = load_manifest(args.manifest)

    output_path = args.output_json or _default_output_path(manifest["dataset"]["name"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved recognition benchmark report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
