import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any
from uuid import UUID


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_embeddings import EmbeddingRecord, fetch_embedding_records


DEFAULT_PROBABLE_THRESHOLD = 0.004
DEFAULT_REVIEW_THRESHOLD = 0.005
DEFAULT_TOP_CRIMINAL_PAIRS = 25
DEFAULT_TOP_FACE_PAIRS_PER_GROUP = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit enrolled face embeddings for suspicious cross-criminal similarity.",
    )
    parser.add_argument(
        "--embedding-version",
        help="Only audit embeddings from a specific embedding_version.",
    )
    parser.add_argument(
        "--probable-threshold",
        type=float,
        default=DEFAULT_PROBABLE_THRESHOLD,
        help=f"Distance threshold for probable duplicate risk (default: {DEFAULT_PROBABLE_THRESHOLD}).",
    )
    parser.add_argument(
        "--review-threshold",
        type=float,
        default=DEFAULT_REVIEW_THRESHOLD,
        help=f"Distance threshold for review-needed risk (default: {DEFAULT_REVIEW_THRESHOLD}).",
    )
    parser.add_argument(
        "--top-criminal-pairs",
        type=int,
        default=DEFAULT_TOP_CRIMINAL_PAIRS,
        help=f"Maximum suspicious criminal-pair groups to include (default: {DEFAULT_TOP_CRIMINAL_PAIRS}).",
    )
    parser.add_argument(
        "--top-face-pairs-per-group",
        type=int,
        default=DEFAULT_TOP_FACE_PAIRS_PER_GROUP,
        help=(
            "Maximum suspicious face pairs to include per criminal-pair group "
            f"(default: {DEFAULT_TOP_FACE_PAIRS_PER_GROUP})."
        ),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to save the audit report as JSON.",
    )
    return parser


def pair_distance(left: EmbeddingRecord, right: EmbeddingRecord) -> float:
    return float(((left.embedding - right.embedding) ** 2).sum() ** 0.5)


def classify_pair_risk(
    distance: float,
    probable_threshold: float,
    review_threshold: float,
) -> str | None:
    if distance <= probable_threshold:
        return "probable_duplicate"
    if distance <= review_threshold:
        return "needs_review"
    return None


def _criminal_identity(record: EmbeddingRecord) -> dict[str, str]:
    return {
        "id": str(record.criminal_id),
        "name": record.criminal_name,
    }


def _face_identity(record: EmbeddingRecord) -> dict[str, Any]:
    return {
        "face_id": str(record.face_id),
        "criminal_id": str(record.criminal_id),
        "criminal_name": record.criminal_name,
        "image_url": record.image_url,
        "embedding_version": record.embedding_version,
        "is_primary": record.is_primary,
    }


def _sorted_pair_key(left: EmbeddingRecord, right: EmbeddingRecord) -> tuple[UUID, UUID]:
    if str(left.criminal_id) <= str(right.criminal_id):
        return left.criminal_id, right.criminal_id
    return right.criminal_id, left.criminal_id


def _ordered_records(left: EmbeddingRecord, right: EmbeddingRecord) -> tuple[EmbeddingRecord, EmbeddingRecord]:
    left_key = (left.criminal_name.lower(), str(left.criminal_id), str(left.face_id))
    right_key = (right.criminal_name.lower(), str(right.criminal_id), str(right.face_id))
    if left_key <= right_key:
        return left, right
    return right, left


def _severity_rank(value: str) -> int:
    if value == "probable_duplicate":
        return 2
    if value == "needs_review":
        return 1
    return 0


def build_duplicate_audit_report(
    records: list[EmbeddingRecord],
    probable_threshold: float,
    review_threshold: float,
    top_criminal_pairs: int,
    top_face_pairs_per_group: int,
    embedding_version: str | None = None,
) -> dict[str, Any]:
    if probable_threshold > review_threshold:
        raise ValueError("probable_threshold must be less than or equal to review_threshold")

    grouped_records: dict[UUID, list[EmbeddingRecord]] = {}
    for record in records:
        grouped_records.setdefault(record.criminal_id, []).append(record)

    criminal_pairs: dict[tuple[UUID, UUID], dict[str, Any]] = {}
    suspicious_face_pair_count = 0

    sorted_records = sorted(records, key=lambda record: (str(record.criminal_id), str(record.face_id)))

    for left_index, left in enumerate(sorted_records):
        for right in sorted_records[left_index + 1:]:
            if left.criminal_id == right.criminal_id:
                continue

            distance = pair_distance(left, right)
            risk_level = classify_pair_risk(distance, probable_threshold, review_threshold)
            if risk_level is None:
                continue

            suspicious_face_pair_count += 1
            pair_key = _sorted_pair_key(left, right)
            group = criminal_pairs.get(pair_key)
            if group is None:
                left_criminal, right_criminal = _ordered_records(left, right)
                group = {
                    "criminal_a": _criminal_identity(left_criminal),
                    "criminal_b": _criminal_identity(right_criminal),
                    "risk_level": risk_level,
                    "minimum_distance": distance,
                    "review_face_pair_count": 0,
                    "probable_duplicate_face_pair_count": 0,
                    "total_cross_face_pair_count": (
                        len(grouped_records[pair_key[0]]) * len(grouped_records[pair_key[1]])
                    ),
                    "face_pairs": [],
                }
                criminal_pairs[pair_key] = group

            group["risk_level"] = (
                risk_level
                if _severity_rank(risk_level) > _severity_rank(group["risk_level"])
                else group["risk_level"]
            )
            group["minimum_distance"] = min(float(group["minimum_distance"]), distance)
            if risk_level == "probable_duplicate":
                group["probable_duplicate_face_pair_count"] += 1
            else:
                group["review_face_pair_count"] += 1

            face_a, face_b = _ordered_records(left, right)
            group["face_pairs"].append(
                {
                    "distance": round(distance, 6),
                    "risk_level": risk_level,
                    "face_a": _face_identity(face_a),
                    "face_b": _face_identity(face_b),
                }
            )

    suspicious_groups = list(criminal_pairs.values())
    for group in suspicious_groups:
        group["minimum_distance"] = round(float(group["minimum_distance"]), 6)
        group["face_pairs"].sort(key=lambda item: (item["distance"], item["face_a"]["face_id"], item["face_b"]["face_id"]))
        group["face_pairs"] = group["face_pairs"][:top_face_pairs_per_group]

    suspicious_groups.sort(
        key=lambda item: (
            -_severity_rank(item["risk_level"]),
            item["minimum_distance"],
            -item["probable_duplicate_face_pair_count"],
            -item["review_face_pair_count"],
        )
    )
    suspicious_groups = suspicious_groups[:top_criminal_pairs]

    flagged_criminal_ids = {
        criminal_id
        for group in suspicious_groups
        for criminal_id in (group["criminal_a"]["id"], group["criminal_b"]["id"])
    }

    return {
        "configuration": {
            "embedding_version": embedding_version,
            "probable_threshold": probable_threshold,
            "review_threshold": review_threshold,
            "top_criminal_pairs": top_criminal_pairs,
            "top_face_pairs_per_group": top_face_pairs_per_group,
        },
        "dataset": {
            "face_count": len(records),
            "criminal_count": len(grouped_records),
        },
        "summary": {
            "flagged_criminal_count": len(flagged_criminal_ids),
            "suspicious_criminal_pair_count": len(suspicious_groups),
            "suspicious_face_pair_count": suspicious_face_pair_count,
            "probable_duplicate_criminal_pair_count": sum(
                1 for group in suspicious_groups if group["risk_level"] == "probable_duplicate"
            ),
            "needs_review_criminal_pair_count": sum(
                1 for group in suspicious_groups if group["risk_level"] == "needs_review"
            ),
        },
        "suspicious_criminal_pairs": suspicious_groups,
    }


def print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("\nFace Database Audit Report")
    print("=" * 26)
    print(
        f"Flagged criminals: {summary['flagged_criminal_count']} | "
        f"criminal-pair findings: {summary['suspicious_criminal_pair_count']} | "
        f"suspicious face pairs: {summary['suspicious_face_pair_count']}"
    )
    print(
        f"Probable duplicates: {summary['probable_duplicate_criminal_pair_count']} | "
        f"Needs review: {summary['needs_review_criminal_pair_count']}"
    )

    findings = report["suspicious_criminal_pairs"]
    if not findings:
        print("\nNo suspicious cross-criminal similarities were found at the configured thresholds.\n")
        return

    print("\nTop suspicious criminal pairs")
    print("-----------------------------")
    for index, finding in enumerate(findings, start=1):
        print(
            f"{index}. {finding['criminal_a']['name']} <-> {finding['criminal_b']['name']} | "
            f"risk={finding['risk_level']} min_distance={finding['minimum_distance']} "
            f"probable_pairs={finding['probable_duplicate_face_pair_count']} "
            f"review_pairs={finding['review_face_pair_count']}"
        )
    print()


async def async_main(args: argparse.Namespace) -> int:
    records = await fetch_embedding_records(args.embedding_version)
    report = build_duplicate_audit_report(
        records=records,
        probable_threshold=args.probable_threshold,
        review_threshold=args.review_threshold,
        top_criminal_pairs=args.top_criminal_pairs,
        top_face_pairs_per_group=args.top_face_pairs_per_group,
        embedding_version=args.embedding_version,
    )

    print_report(report)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved JSON report to {args.output_json}")

    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
