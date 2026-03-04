import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a governance-friendly threshold and release recommendation from a benchmark report.",
    )
    parser.add_argument("benchmark_report", type=Path, help="Path to a recognition benchmark JSON report.")
    parser.add_argument(
        "--min-top1-rate",
        type=float,
        default=0.9,
        help="Minimum own-template top-1 rate for a GO decision (default: 0.90).",
    )
    parser.add_argument(
        "--max-match-far",
        type=float,
        default=0.01,
        help="Maximum FAR allowed at the recommended match threshold for a GO decision (default: 0.01).",
    )
    parser.add_argument(
        "--min-evaluated-probe-faces",
        type=int,
        default=20,
        help="Minimum evaluated probe faces required for a GO decision (default: 20).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to save the threshold recommendation JSON.",
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        help="Optional path to save the threshold recommendation as Markdown.",
    )
    return parser


def build_go_no_go_report(
    benchmark_report: dict[str, Any],
    *,
    min_top1_rate: float,
    max_match_far: float,
    min_evaluated_probe_faces: int,
) -> dict[str, Any]:
    template_calibration = benchmark_report["template_calibration"]
    ranking = template_calibration["ranking"]
    pair_threshold_report = benchmark_report["pair_evaluation"]["threshold_report"]
    recommended_policy = template_calibration["recommended_policy"]

    match_threshold = recommended_policy["match_threshold"]
    match_metrics = pair_threshold_report["recommended"].get("far_le_0.010") or pair_threshold_report["recommended"].get("best_balanced_accuracy") or {}
    top1_rate = ranking.get("own_template_top1_rate")
    evaluated_probes = template_calibration["dataset"]["evaluated_probe_faces"]
    match_far = match_metrics.get("far")

    checks = {
        "enough_probe_faces": {
            "passed": evaluated_probes >= min_evaluated_probe_faces,
            "actual": evaluated_probes,
            "required": min_evaluated_probe_faces,
        },
        "own_template_top1_rate": {
            "passed": top1_rate is not None and top1_rate >= min_top1_rate,
            "actual": top1_rate,
            "required": min_top1_rate,
        },
        "match_far": {
            "passed": match_far is not None and match_far <= max_match_far,
            "actual": match_far,
            "required": max_match_far,
        },
    }

    failed_checks = [name for name, check in checks.items() if not check["passed"]]
    if not failed_checks:
        status = "go"
    elif "enough_probe_faces" in failed_checks and len(failed_checks) == 1:
        status = "conditional"
    else:
        status = "no_go"

    return {
        "report_type": "threshold_governance_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": benchmark_report["dataset"],
        "benchmark_report_generated_at": benchmark_report.get("generated_at"),
        "recommended_policy": recommended_policy,
        "pair_threshold_recommendations": pair_threshold_report["recommended"],
        "checks": checks,
        "decision": {
            "status": status,
            "failed_checks": failed_checks,
            "summary": (
                "Benchmark supports rollout."
                if status == "go"
                else "Benchmark data is incomplete; review manually before rollout."
                if status == "conditional"
                else "Benchmark does not support rollout."
            ),
            "release_checklist": [
                "Attach the benchmark report JSON to the release or model-change record.",
                "Record the chosen match and possible-match thresholds in deployment notes.",
                "Document the benchmark dataset name and image count.",
                "Do not change production thresholds without a new benchmark report.",
            ],
        },
        "threshold_summary": {
            "recommended_match_threshold": match_threshold,
            "recommended_possible_match_threshold": recommended_policy["possible_match_threshold"],
            "recommended_match_separation_margin": recommended_policy["match_separation_margin"],
            "recommended_possible_match_separation_margin": recommended_policy["possible_match_separation_margin"],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Threshold Governance Report",
        "",
        f"- Decision: `{report['decision']['status']}`",
        f"- Dataset: `{report['dataset']['name']}`",
        f"- Evaluated images: `{report['dataset']['evaluated_image_count']}`",
        f"- Failed images: `{report['dataset']['failed_image_count']}`",
        "",
        "## Recommended Policy",
        "",
        f"- Match threshold: `{report['threshold_summary']['recommended_match_threshold']}`",
        f"- Possible-match threshold: `{report['threshold_summary']['recommended_possible_match_threshold']}`",
        f"- Match separation margin: `{report['threshold_summary']['recommended_match_separation_margin']}`",
        f"- Possible-match separation margin: `{report['threshold_summary']['recommended_possible_match_separation_margin']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in report["checks"].items():
        lines.append(
            f"- `{name}`: {'PASS' if check['passed'] else 'FAIL'} "
            f"(actual=`{check['actual']}`, required=`{check['required']}`)"
        )
    lines.extend(
        [
            "",
            "## Release Checklist",
            "",
        ]
    )
    for item in report["decision"]["release_checklist"]:
        lines.append(f"- [ ] {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    benchmark_report = json.loads(args.benchmark_report.read_text(encoding="utf-8"))
    report = build_go_no_go_report(
        benchmark_report,
        min_top1_rate=args.min_top1_rate,
        max_match_far=args.max_match_far,
        min_evaluated_probe_faces=args.min_evaluated_probe_faces,
    )

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved governance JSON report to {args.output_json}")
    else:
        print(json.dumps(report, indent=2))

    if args.output_markdown:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(render_markdown(report), encoding="utf-8")
        print(f"Saved governance markdown report to {args.output_markdown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
