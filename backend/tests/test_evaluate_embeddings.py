import random
from uuid import uuid4

import numpy as np

from scripts.evaluate_embeddings import (
    EmbeddingRecord,
    compute_threshold_metrics,
    evaluate_thresholds,
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
        embedding=np.asarray(values, dtype=np.float32),
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
