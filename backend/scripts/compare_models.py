import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_threshold_report import build_go_no_go_report, render_markdown  # noqa: E402
from scripts.run_recognition_benchmark import load_manifest, run_benchmark  # noqa: E402
from src.schemas.model_version import ModelBenchmarkSummary  # noqa: E402
from src.services.recognition_policy_service import (  # noqa: E402
    DEFAULT_MATCH_SEPARATION_MARGIN,
    DEFAULT_MATCH_THRESHOLD,
    DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
    DEFAULT_POSSIBLE_MATCH_THRESHOLD,
)
from src.services.ai.strategies import (  # noqa: E402
    DEFAULT_EMBEDDING_VERSION,
    FACENET_EMBEDDING_VERSION,
    get_model_version_metadata,
)


STATUS_RANK = {
    "go": 2,
    "conditional": 1,
    "no_go": 0,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare multiple embedding models against the same held-out benchmark manifest.",
    )
    parser.add_argument("manifest", type=Path, help="Path to the benchmark manifest JSON.")
    parser.add_argument(
        "--candidate",
        action="append",
        dest="candidates",
        help=(
            "Candidate embedding version to evaluate. "
            "Repeat for multiple models. Defaults to tracenet_v1 and facenet_vggface2."
        ),
    )
    parser.add_argument(
        "--candidate-model-path",
        action="append",
        default=[],
        help="Optional custom model path mapping in the form version=/abs/path/to/checkpoint.pth",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        help="Optional directory for per-model benchmark and threshold reports.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to save the model comparison JSON.",
    )
    parser.add_argument(
        "--output-markdown",
        type=Path,
        help="Optional path to save the model comparison Markdown.",
    )
    parser.add_argument("--min-top1-rate", type=float, default=0.9)
    parser.add_argument("--max-match-far", type=float, default=0.01)
    parser.add_argument("--min-evaluated-probe-faces", type=int, default=20)
    return parser


def parse_model_paths(raw_values: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for item in raw_values:
        if "=" not in item:
            raise ValueError(f"Invalid --candidate-model-path value '{item}'. Expected version=/path/to/file.")
        version, raw_path = item.split("=", 1)
        parsed[version.strip()] = Path(raw_path).expanduser().resolve()
    return parsed


def build_benchmark_args(
    manifest: Path,
    *,
    embedding_version: str,
    model_path: Path | None,
    output_json: Path,
) -> SimpleNamespace:
    return SimpleNamespace(
        manifest=manifest,
        output_json=output_json,
        current_threshold=0.01,
        current_match_threshold=DEFAULT_MATCH_THRESHOLD,
        current_possible_match_threshold=DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        current_match_separation_margin=DEFAULT_MATCH_SEPARATION_MARGIN,
        current_possible_match_separation_margin=DEFAULT_POSSIBLE_MATCH_SEPARATION_MARGIN,
        grid_size=200,
        embedding_version=embedding_version,
        model_path=model_path,
    )


def choose_winner(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None

    def ranking_key(item: dict[str, Any]) -> tuple[float, float, float]:
        threshold_report = item["threshold_report"]
        status = threshold_report["decision"]["status"]
        top1_rate = threshold_report["checks"]["own_template_top1_rate"]["actual"] or 0.0
        match_far = threshold_report["checks"]["match_far"]["actual"]
        if match_far is None:
            match_far = 1.0
        return (STATUS_RANK.get(status, -1), top1_rate, -match_far)

    return max(candidates, key=ranking_key)


def render_comparison_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Model Comparison Report",
        "",
        f"- Dataset: `{report['dataset']['name']}`",
        f"- Candidate count: `{len(report['candidates'])}`",
        "",
    ]
    winner = report.get("winner")
    if winner is not None:
        lines.extend(
            [
                "## Recommended Winner",
                "",
                f"- Version: `{winner['summary']['version']}`",
                f"- Display name: `{winner['summary']['display_name']}`",
                f"- Decision: `{winner['summary']['decision_status']}`",
                f"- Top-1 rate: `{winner['summary']['own_template_top1_rate']}`",
                f"- Match FAR: `{winner['summary']['match_far']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Candidates",
            "",
        ]
    )
    for candidate in report["candidates"]:
        summary = candidate["summary"]
        lines.append(
            f"- `{summary['version']}` / `{summary['display_name']}`: "
            f"decision=`{summary['decision_status']}`, "
            f"top1=`{summary['own_template_top1_rate']}`, "
            f"match_far=`{summary['match_far']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    dataset_name = manifest["dataset"]["name"]
    candidates = args.candidates or [DEFAULT_EMBEDDING_VERSION, FACENET_EMBEDDING_VERSION]
    model_paths = parse_model_paths(args.candidate_model_path)
    artifacts_dir = args.artifacts_dir or PROJECT_ROOT / "uploads" / "benchmarks" / "comparisons" / dataset_name

    comparison_entries: list[dict[str, Any]] = []
    for candidate in candidates:
        safe_candidate = candidate.replace("/", "-")
        benchmark_path = artifacts_dir / f"{safe_candidate}-benchmark.json"
        threshold_path = artifacts_dir / f"{safe_candidate}-threshold.json"
        threshold_md_path = artifacts_dir / f"{safe_candidate}-threshold.md"
        benchmark_args = build_benchmark_args(
            args.manifest,
            embedding_version=candidate,
            model_path=model_paths.get(candidate),
            output_json=benchmark_path,
        )

        try:
            benchmark_report = run_benchmark(benchmark_args)
        except Exception as exc:
            comparison_entries.append(
                {
                    "summary": ModelBenchmarkSummary(
                        version=candidate,
                        display_name=get_model_version_metadata(candidate)["display_name"],
                        decision_status="unavailable",
                        own_template_top1_rate=None,
                        match_far=None,
                        evaluated_image_count=0,
                        failed_image_count=0,
                        benchmark_report_path=None,
                        threshold_report_path=None,
                    ).model_dump(),
                    "error": str(exc),
                }
            )
            continue

        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_path.write_text(json.dumps(benchmark_report, indent=2), encoding="utf-8")
        threshold_report = build_go_no_go_report(
            benchmark_report,
            min_top1_rate=args.min_top1_rate,
            max_match_far=args.max_match_far,
            min_evaluated_probe_faces=args.min_evaluated_probe_faces,
        )
        threshold_path.write_text(json.dumps(threshold_report, indent=2), encoding="utf-8")
        threshold_md_path.write_text(render_markdown(threshold_report), encoding="utf-8")

        summary = ModelBenchmarkSummary(
            version=candidate,
            display_name=get_model_version_metadata(candidate)["display_name"],
            decision_status=threshold_report["decision"]["status"],
            own_template_top1_rate=threshold_report["checks"]["own_template_top1_rate"]["actual"],
            match_far=threshold_report["checks"]["match_far"]["actual"],
            evaluated_image_count=benchmark_report["dataset"]["evaluated_image_count"],
            failed_image_count=benchmark_report["dataset"]["failed_image_count"],
            benchmark_report_path=str(benchmark_path),
            threshold_report_path=str(threshold_path),
        )
        comparison_entries.append(
            {
                "summary": summary.model_dump(),
                "benchmark_report": benchmark_report,
                "threshold_report": threshold_report,
            }
        )

    winner = choose_winner(
        [entry for entry in comparison_entries if "threshold_report" in entry]
    )
    report = {
        "report_type": "model_comparison",
        "dataset": manifest["dataset"],
        "candidates": comparison_entries,
        "winner": winner,
    }

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved model comparison report to {args.output_json}")
    else:
        print(json.dumps(report, indent=2))

    if args.output_markdown:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(render_comparison_markdown(report), encoding="utf-8")
        print(f"Saved model comparison markdown report to {args.output_markdown}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
