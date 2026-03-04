from datetime import datetime, timedelta, timezone

from scripts.check_benchmark_gate import evaluate_gate


def make_report(*, status: str = "go", generated_at: datetime | None = None, dataset_name: str = "sample"):
    return {
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "dataset": {"name": dataset_name},
        "decision": {"status": status},
    }


def test_evaluate_gate_passes_go_report():
    passed, failures = evaluate_gate(
        make_report(status="go"),
        allow_conditional=False,
        max_age_days=30,
        require_dataset_name=None,
    )

    assert passed is True
    assert failures == []


def test_evaluate_gate_rejects_old_or_wrong_dataset():
    passed, failures = evaluate_gate(
        make_report(
            status="go",
            generated_at=datetime.now(timezone.utc) - timedelta(days=45),
            dataset_name="other",
        ),
        allow_conditional=False,
        max_age_days=30,
        require_dataset_name="expected",
    )

    assert passed is False
    assert any("report_too_old" in failure for failure in failures)
    assert any("dataset_name_mismatch" in failure for failure in failures)


def test_evaluate_gate_allows_conditional_when_requested():
    passed, failures = evaluate_gate(
        make_report(status="conditional"),
        allow_conditional=True,
        max_age_days=30,
        require_dataset_name=None,
    )

    assert passed is True
    assert failures == []
