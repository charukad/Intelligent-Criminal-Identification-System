import random
from pathlib import Path
from uuid import uuid4

import numpy as np

from scripts.build_pair_benchmark import build_manifest, discover_identity_images
from scripts.generate_threshold_report import build_go_no_go_report


def test_discover_identity_images_filters_small_identities(tmp_path: Path):
    alpha = tmp_path / "alpha"
    bravo = tmp_path / "bravo"
    alpha.mkdir()
    bravo.mkdir()
    (alpha / "a1.jpg").write_bytes(b"1")
    (alpha / "a2.jpg").write_bytes(b"2")
    (bravo / "b1.jpg").write_bytes(b"1")

    identities = discover_identity_images(
        tmp_path,
        min_images_per_identity=2,
        max_images_per_identity=0,
        rng=random.Random(42),
    )

    assert list(identities.keys()) == ["alpha"]
    assert len(identities["alpha"]) == 2


def test_build_manifest_creates_deterministic_pair_sets(tmp_path: Path):
    alpha = tmp_path / "alpha"
    bravo = tmp_path / "bravo"
    alpha.mkdir()
    bravo.mkdir()
    alpha_paths = []
    bravo_paths = []
    for index in range(3):
        path = alpha / f"a{index}.jpg"
        path.write_bytes(b"alpha")
        alpha_paths.append(path)
    for index in range(2):
        path = bravo / f"b{index}.jpg"
        path.write_bytes(b"bravo")
        bravo_paths.append(path)

    manifest = build_manifest(
        dataset_root=tmp_path,
        dataset_name="unit-test-benchmark",
        identity_images={"alpha": alpha_paths, "bravo": bravo_paths},
        max_positive_pairs=10,
        max_negative_pairs=10,
        seed=42,
    )

    assert manifest["dataset"]["identity_count"] == 2
    assert manifest["dataset"]["image_count"] == 5
    assert manifest["pairs"]["metadata"]["total_possible_positive_pairs"] == 4
    assert manifest["pairs"]["metadata"]["total_possible_negative_pairs"] == 6
    assert len(manifest["pairs"]["positive"]) == 4
    assert len(manifest["pairs"]["negative"]) == 6


def test_build_go_no_go_report_marks_no_go_when_core_checks_fail():
    benchmark_report = {
        "generated_at": "2026-03-03T00:00:00+00:00",
        "dataset": {
            "name": "sample",
            "evaluated_image_count": 40,
            "failed_image_count": 2,
        },
        "pair_evaluation": {
            "threshold_report": {
                "recommended": {
                    "far_le_0.010": {"threshold": 0.0042, "far": 0.02},
                    "best_balanced_accuracy": {"threshold": 0.005, "far": 0.02},
                }
            }
        },
        "template_calibration": {
            "dataset": {"evaluated_probe_faces": 12},
            "ranking": {"own_template_top1_rate": 0.7},
            "recommended_policy": {
                "match_threshold": 0.0042,
                "possible_match_threshold": 0.0061,
                "match_separation_margin": 0.001,
                "possible_match_separation_margin": 0.0004,
            },
        },
    }

    report = build_go_no_go_report(
        benchmark_report,
        min_top1_rate=0.9,
        max_match_far=0.01,
        min_evaluated_probe_faces=20,
    )

    assert report["decision"]["status"] == "no_go"
    assert "own_template_top1_rate" in report["decision"]["failed_checks"]
    assert "match_far" in report["decision"]["failed_checks"]
