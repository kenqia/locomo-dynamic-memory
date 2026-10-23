"""Standalone report output stays readable and safe."""

from locomo_memory.report_html import render_evaluation_report_html, render_experiment_report_html


def sample_run():
    return {
        "run_id": "run-1",
        "kind": "development",
        "status": "completed",
        "elapsed_seconds": 3.25,
        "strategies": ["dynamic"],
        "progress": {"total": 1, "succeeded": 1},
        "input": {"samples": [{"question": "Where is <Alex>?"}]},
        "summary": {
            "dynamic": {
                "qa": {"mean": 1.0, "scored": 1},
                "execution": {"planned": 1, "succeeded": 1, "success_rate": 1.0},
                "baseline_run_score": {"value": 1.0, "status": "complete"},
            }
        },
        "results": [{
            "sample_index": 0,
            "strategy": "dynamic",
            "qa": {"value": 1.0},
            "trace": {"answer": {"status": "sufficient", "answer": "<Paris>"}},
        }],
    }


def test_evaluation_html_is_standalone_and_escapes_values():
    html = render_evaluation_report_html(sample_run())
    assert "<!doctype html>" in html
    assert "动态记忆评测报告" in html
    assert "完整动态系统" in html
    assert "Where is &lt;Alex&gt;?" in html
    assert "&lt;Paris&gt;" in html
    assert "<Paris>" not in html
    assert 'src="http' not in html and 'href="http' not in html


def test_experiment_html_keeps_scope_and_blockers_without_run():
    html = render_experiment_report_html(
        {"status": "prepared_offline", "updated_at": "2026-10-22", "blockers": ["missing_credentials"]},
        "smoke",
    )
    assert "开发集实验报告 · smoke" in html
    assert "missing_credentials" in html
    assert "prepared_offline" in html
