import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a repeatable face-benchmark manifest from a directory tree of identity-labelled images."
        ),
    )
    parser.add_argument(
        "dataset_root",
        type=Path,
        help="Root directory containing one subdirectory per identity.",
    )
    parser.add_argument(
        "--dataset-name",
        default="local-face-benchmark",
        help="Name stored in the manifest metadata.",
    )
    parser.add_argument(
        "--min-images-per-identity",
        type=int,
        default=2,
        help="Minimum number of images required to include an identity (default: 2).",
    )
    parser.add_argument(
        "--max-images-per-identity",
        type=int,
        default=0,
        help="Optional cap per identity after deterministic sampling. Use 0 for no cap.",
    )
    parser.add_argument(
        "--max-positive-pairs",
        type=int,
        default=10000,
        help="Maximum positive pairs to keep in the manifest (default: 10000).",
    )
    parser.add_argument(
        "--max-negative-pairs",
        type=int,
        default=10000,
        help="Maximum negative pairs to keep in the manifest (default: 10000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic sampling (default: 42).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        help="Path to write the benchmark manifest JSON.",
    )
    return parser


def discover_identity_images(
    dataset_root: Path,
    *,
    min_images_per_identity: int,
    max_images_per_identity: int,
    rng: random.Random,
) -> dict[str, list[Path]]:
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset root does not exist: {dataset_root}")
    if not dataset_root.is_dir():
        raise ValueError(f"Dataset root must be a directory: {dataset_root}")

    identities: dict[str, list[Path]] = {}
    for identity_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        images = sorted(
            path
            for path in identity_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if len(images) < min_images_per_identity:
            continue
        if max_images_per_identity > 0 and len(images) > max_images_per_identity:
            images = sorted(rng.sample(images, max_images_per_identity))
        identities[identity_dir.name] = images

    return identities


def build_manifest(
    *,
    dataset_root: Path,
    dataset_name: str,
    identity_images: dict[str, list[Path]],
    max_positive_pairs: int,
    max_negative_pairs: int,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    images: list[dict[str, Any]] = []
    image_id_by_path: dict[Path, str] = {}

    for identity_label, paths in sorted(identity_images.items()):
        for index, image_path in enumerate(paths, start=1):
            image_id = f"{identity_label}:{index:04d}"
            relative_path = image_path.relative_to(dataset_root)
            image_id_by_path[image_path] = image_id
            images.append(
                {
                    "image_id": image_id,
                    "identity": identity_label,
                    "path": relative_path.as_posix(),
                }
            )

    positive_pairs: list[dict[str, Any]] = []
    negative_pairs: list[dict[str, Any]] = []

    grouped_paths: dict[str, list[Path]] = defaultdict(list)
    for identity_label, paths in identity_images.items():
        grouped_paths[identity_label].extend(paths)

    total_possible_positive_pairs = 0
    for identity_label, paths in grouped_paths.items():
        for left_index, left_path in enumerate(paths):
            for right_path in paths[left_index + 1:]:
                total_possible_positive_pairs += 1
                positive_pairs.append(
                    {
                        "pair_id": f"pos:{identity_label}:{len(positive_pairs) + 1:05d}",
                        "left_image_id": image_id_by_path[left_path],
                        "right_image_id": image_id_by_path[right_path],
                        "label": "same_identity",
                    }
                )

    if len(positive_pairs) > max_positive_pairs:
        positive_pairs = sorted(rng.sample(positive_pairs, max_positive_pairs), key=lambda item: item["pair_id"])

    identity_labels = sorted(grouped_paths.keys())
    total_possible_negative_pairs = 0
    for left_identity_index, left_identity in enumerate(identity_labels):
        for right_identity in identity_labels[left_identity_index + 1:]:
            left_paths = grouped_paths[left_identity]
            right_paths = grouped_paths[right_identity]
            total_possible_negative_pairs += len(left_paths) * len(right_paths)
            for left_path in left_paths:
                for right_path in right_paths:
                    negative_pairs.append(
                        {
                            "pair_id": f"neg:{left_identity}:{right_identity}:{len(negative_pairs) + 1:05d}",
                            "left_image_id": image_id_by_path[left_path],
                            "right_image_id": image_id_by_path[right_path],
                            "label": "different_identity",
                        }
                    )

    if len(negative_pairs) > max_negative_pairs:
        negative_pairs = sorted(rng.sample(negative_pairs, max_negative_pairs), key=lambda item: item["pair_id"])

    return {
        "manifest_version": 1,
        "dataset": {
            "name": dataset_name,
            "dataset_root": str(dataset_root.resolve()),
            "identity_count": len(identity_images),
            "image_count": len(images),
            "seed": seed,
        },
        "images": images,
        "pairs": {
            "positive": positive_pairs,
            "negative": negative_pairs,
            "metadata": {
                "total_possible_positive_pairs": total_possible_positive_pairs,
                "total_possible_negative_pairs": total_possible_negative_pairs,
                "sampled_positive_pairs": len(positive_pairs),
                "sampled_negative_pairs": len(negative_pairs),
            },
        },
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    rng = random.Random(args.seed)

    identity_images = discover_identity_images(
        args.dataset_root,
        min_images_per_identity=args.min_images_per_identity,
        max_images_per_identity=args.max_images_per_identity,
        rng=rng,
    )
    if not identity_images:
        raise SystemExit("No eligible identities found in dataset root.")

    manifest = build_manifest(
        dataset_root=args.dataset_root,
        dataset_name=args.dataset_name,
        identity_images=identity_images,
        max_positive_pairs=args.max_positive_pairs,
        max_negative_pairs=args.max_negative_pairs,
        seed=args.seed,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Saved benchmark manifest with {manifest['dataset']['image_count']} images, "
        f"{manifest['pairs']['metadata']['sampled_positive_pairs']} positive pairs, and "
        f"{manifest['pairs']['metadata']['sampled_negative_pairs']} negative pairs to {args.output_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
