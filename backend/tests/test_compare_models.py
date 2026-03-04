from pathlib import Path

from scripts.compare_models import choose_winner, parse_model_paths, render_comparison_markdown


def test_parse_model_paths_parses_version_mapping(tmp_path: Path):
    checkpoint = tmp_path / "candidate.pth"
    checkpoint.write_bytes(b"checkpoint")

    parsed = parse_model_paths([f"tracenet_v2={checkpoint}"])

    assert parsed["tracenet_v2"] == checkpoint.resolve()


def test_choose_winner_prefers_go_status_then_top1_rate():
    winner = choose_winner(
        [
            {
                "summary": {"version": "tracenet_v1"},
                "threshold_report": {
                    "decision": {"status": "no_go"},
                    "checks": {
                        "own_template_top1_rate": {"actual": 0.95},
                        "match_far": {"actual": 0.001},
                    },
                },
            },
            {
                "summary": {"version": "facenet_vggface2"},
                "threshold_report": {
                    "decision": {"status": "go"},
                    "checks": {
                        "own_template_top1_rate": {"actual": 0.91},
                        "match_far": {"actual": 0.005},
                    },
                },
            },
        ]
    )

    assert winner is not None
    assert winner["summary"]["version"] == "facenet_vggface2"


def test_render_comparison_markdown_mentions_winner():
    markdown = render_comparison_markdown(
        {
            "dataset": {"name": "face-2-heldout"},
            "candidates": [
                {
                    "summary": {
                        "version": "tracenet_v1",
                        "display_name": "TraceNet v1",
                        "decision_status": "no_go",
                        "own_template_top1_rate": 0.3,
                        "match_far": 0.009,
                    }
                }
            ],
            "winner": {
                "summary": {
                    "version": "tracenet_v1",
                    "display_name": "TraceNet v1",
                    "decision_status": "no_go",
                    "own_template_top1_rate": 0.3,
                    "match_far": 0.009,
                }
            },
        }
    )

    assert "Model Comparison Report" in markdown
    assert "TraceNet v1" in markdown
    assert "face-2-heldout" in markdown
