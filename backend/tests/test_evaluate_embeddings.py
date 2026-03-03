from datetime import datetime, timezone
import random
from uuid import uuid4

import numpy as np

from scripts.evaluate_embeddings import (
    EmbeddingRecord,
    TemplateRecord,
    compute_threshold_metrics,
    evaluate_template_probes,
    evaluate_thresholds,
    recommend_policy_settings,
    sample_negative_pairs,
    sample_positive_pairs,
    summarize_distances,
)


def make_record(criminal_id, values, criminal_name="Test Person"):
    return EmbeddingRecord(
        face_id=uuid4(),
        criminal_id=criminal_id,
        criminal_name=criminal_name,
        image_url="/uploads/test.png",
        embedding_version="v1",
        is_primary=False,
        created_at=datetime.now(timezone.utc),
        quality_status="accepted",
        template_role="archived",
        template_distance=None,
        embedding=np.asarray(values, dtype=np.float32),
    )


def make_template(criminal_id, values, criminal_name="Test Person"):
    return TemplateRecord(
        criminal_id=criminal_id,
        criminal_name=criminal_name,
        template_version="tracenet_template_v1",
        embedding_version="v1",
        active_face_count=2,
        support_face_count=1,
        outlier_face_count=0,
        template_embedding=np.asarray(values, dtype=np.float32),
    )


def test_sample_positive_pairs_only_within_same_criminal():
    criminal_a = uuid4()
    criminal_b = uuid4()
    records = [
        make_record(criminal_a, [0.0, 0.0]),
        make_record(criminal_a, [0.0, 1.0]),
        make_record(criminal_b, [5.0, 5.0]),
    ]

    distances, metadata = sample_positive_pairs(records, max_pairs=10, rng=random.Random(42))

    assert metadata["eligible_identity_count"] == 1
    assert metadata["total_possible_pairs"] == 1
    assert metadata["sampled_pairs"] == 1
    assert np.allclose(distances, np.asarray([1.0], dtype=np.float32))


def test_sample_negative_pairs_only_across_different_criminals():
    criminal_a = uuid4()
    criminal_b = uuid4()
    records = [
        make_record(criminal_a, [0.0, 0.0]),
        make_record(criminal_a, [0.0, 1.0]),
        make_record(criminal_b, [3.0, 4.0]),
    ]

    distances, metadata = sample_negative_pairs(
        records,
        positive_pair_count=1,
        max_pairs=10,
        rng=random.Random(42),
    )

    assert metadata["total_possible_pairs"] == 2
    assert metadata["sampled_pairs"] == 2
    assert np.allclose(
        np.sort(distances),
        np.sort(np.asarray([5.0, 4.2426405], dtype=np.float32)),
        atol=1e-6,
    )


def test_evaluate_thresholds_recommends_balanced_cutoff():
    positive = np.asarray([0.002, 0.004, 0.006], dtype=np.float32)
    negative = np.asarray([0.02, 0.03, 0.04], dtype=np.float32)

    report = evaluate_thresholds(positive, negative, current_threshold=0.01, grid_size=20)

    assert report["current_threshold"]["far"] == 0.0
    assert report["current_threshold"]["tar"] == 1.0
    assert report["recommended"]["best_balanced_accuracy"]["threshold"] <= 0.02
    assert report["recommended"]["best_balanced_accuracy"]["balanced_accuracy"] == 1.0


def test_compute_threshold_metrics_handles_empty_negative_set():
    positive = np.asarray([0.002, 0.004], dtype=np.float32)
    negative = np.asarray([], dtype=np.float32)

    metrics = compute_threshold_metrics(positive, negative, threshold=0.01)

    assert metrics["tar"] == 1.0
    assert metrics["far"] is None
    assert metrics["balanced_accuracy"] is None


def test_summarize_distances_returns_empty_shape():
    summary = summarize_distances(np.asarray([], dtype=np.float32))

    assert summary["count"] == 0
    assert summary["mean"] is None
    assert summary["p95"] is None


def test_recommend_policy_settings_prefers_far_targets_and_gap_percentiles():
    threshold_report = {
        "recommended": {
            "far_le_0.010": {"threshold": 0.0042},
            "far_le_0.050": {"threshold": 0.0061},
        }
    }
    separation_gaps = np.asarray([0.001, 0.0014, 0.002, 0.0025], dtype=np.float32)

    recommendation = recommend_policy_settings(
        threshold_report=threshold_report,
        positive_probe_distances=np.asarray([0.0025, 0.0035, 0.0045, 0.0062], dtype=np.float32),
        separation_gaps=separation_gaps,
        top1_positive_separation_gaps=np.asarray([0.001, 0.0014, 0.0025], dtype=np.float32),
        fallback_match_threshold=0.0045,
        fallback_possible_match_threshold=0.0075,
        fallback_match_separation_margin=0.0012,
        fallback_possible_match_separation_margin=0.0004,
    )

    assert recommendation["match_threshold"] == 0.0042
    assert recommendation["possible_match_threshold"] == 0.0061
    assert recommendation["match_threshold_source"] == "far_le_0.010"
    assert recommendation["possible_match_threshold_source"] == "far_le_0.050"
    assert recommendation["match_separation_margin"] > 0
    assert recommendation["possible_match_separation_margin"] <= recommendation["match_separation_margin"]


def test_evaluate_template_probes_uses_holdout_identity_templates():
    criminal_a = uuid4()
    criminal_b = uuid4()
    records = [
        make_record(criminal_a, [1.0, 0.0], criminal_name="Alpha"),
        make_record(criminal_a, [0.99, 0.01], criminal_name="Alpha"),
        make_record(criminal_b, [-1.0, 0.0], criminal_name="Bravo"),
        make_record(criminal_b, [-0.99, -0.01], criminal_name="Bravo"),
    ]
    templates = [
        make_template(criminal_a, [0.999, 0.001], criminal_name="Alpha"),
        make_template(criminal_b, [-0.999, -0.001], criminal_name="Bravo"),
    ]

    report = evaluate_template_probes(
        records,
        templates,
        current_match_threshold=0.2,
        current_possible_match_threshold=0.4,
        current_match_separation_margin=0.05,
        current_possible_match_separation_margin=0.02,
        max_probes=10,
        rng=random.Random(42),
        grid_size=20,
    )

    assert report["dataset"]["evaluated_probe_faces"] == 4
    assert report["ranking"]["own_template_top1_count"] == 4
    assert report["ranking"]["own_template_top1_rate"] == 1.0
    assert report["positive_probe_distances"]["distance_summary"]["p95"] < 0.05
    assert report["nearest_other_template_distances"]["distance_summary"]["min"] > 1.5
    assert report["top1_positive_separation_gaps"]["distance_summary"]["min"] > 1.5
    assert report["recommended_policy"]["match_threshold"] <= report["recommended_policy"]["possible_match_threshold"]
