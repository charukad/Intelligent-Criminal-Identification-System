from uuid import uuid4

import numpy as np
import pytest

from scripts.audit_face_database import (
    build_duplicate_audit_report,
    classify_pair_risk,
)
from scripts.evaluate_embeddings import EmbeddingRecord


def make_record(criminal_id, values, criminal_name):
    return EmbeddingRecord(
        face_id=uuid4(),
        criminal_id=criminal_id,
        criminal_name=criminal_name,
        image_url="/uploads/test.png",
        embedding_version="tracenet_v1",
        is_primary=False,
        embedding=np.asarray(values, dtype=np.float32),
    )


def test_classify_pair_risk_respects_threshold_bands():
    assert classify_pair_risk(0.0035, probable_threshold=0.004, review_threshold=0.005) == "probable_duplicate"
    assert classify_pair_risk(0.0045, probable_threshold=0.004, review_threshold=0.005) == "needs_review"
    assert classify_pair_risk(0.006, probable_threshold=0.004, review_threshold=0.005) is None


def test_build_duplicate_audit_report_groups_cross_criminal_pairs():
    criminal_a = uuid4()
    criminal_b = uuid4()
    criminal_c = uuid4()
    records = [
        make_record(criminal_a, [0.0, 0.0], "Alpha One"),
        make_record(criminal_a, [0.0, 0.01], "Alpha One"),
        make_record(criminal_b, [0.0, 0.002], "Beta Two"),
        make_record(criminal_b, [0.0, 0.003], "Beta Two"),
        make_record(criminal_c, [1.0, 1.0], "Gamma Three"),
    ]

    report = build_duplicate_audit_report(
        records=records,
        probable_threshold=0.004,
        review_threshold=0.005,
        top_criminal_pairs=10,
        top_face_pairs_per_group=3,
        embedding_version="tracenet_v1",
    )

    assert report["summary"]["flagged_criminal_count"] == 2
    assert report["summary"]["suspicious_criminal_pair_count"] == 1
    assert report["summary"]["probable_duplicate_criminal_pair_count"] == 1

    finding = report["suspicious_criminal_pairs"][0]
    assert finding["criminal_a"]["name"] == "Alpha One"
    assert finding["criminal_b"]["name"] == "Beta Two"
    assert finding["risk_level"] == "probable_duplicate"
    assert finding["probable_duplicate_face_pair_count"] >= 1
    assert finding["minimum_distance"] <= 0.004
    assert len(finding["face_pairs"]) <= 3


def test_build_duplicate_audit_report_returns_empty_findings_when_no_pairs_are_close():
    criminal_a = uuid4()
    criminal_b = uuid4()
    records = [
        make_record(criminal_a, [0.0, 0.0], "Alpha One"),
        make_record(criminal_b, [1.0, 1.0], "Beta Two"),
    ]

    report = build_duplicate_audit_report(
        records=records,
        probable_threshold=0.004,
        review_threshold=0.005,
        top_criminal_pairs=10,
        top_face_pairs_per_group=3,
        embedding_version=None,
    )

    assert report["summary"]["flagged_criminal_count"] == 0
    assert report["summary"]["suspicious_criminal_pair_count"] == 0
    assert report["suspicious_criminal_pairs"] == []


def test_build_duplicate_audit_report_rejects_invalid_threshold_order():
    criminal_a = uuid4()
    criminal_b = uuid4()
    records = [
        make_record(criminal_a, [0.0, 0.0], "Alpha One"),
        make_record(criminal_b, [0.0, 0.002], "Beta Two"),
    ]

    with pytest.raises(ValueError):
        build_duplicate_audit_report(
            records=records,
            probable_threshold=0.006,
            review_threshold=0.005,
            top_criminal_pairs=10,
            top_face_pairs_per_group=3,
            embedding_version=None,
        )
