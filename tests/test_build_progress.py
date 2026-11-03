import pytest

from locomo_memory.build_progress import summarize_build_progress


def build(status: str, phase: str, *, succeeded: int = 0, failed: int = 0, pending: int = 4):
    return {
        "status": status,
        "phase": phase,
        "progress": {"total": 4, "succeeded": succeeded, "failed": failed, "pending": pending},
    }


def test_extraction_uses_fragment_progress_within_first_quarter():
    summary = summarize_build_progress(build("running", "extraction", succeeded=2, pending=2))
    assert summary["value"] == pytest.approx(0.125)
    assert summary["stage"] == 1
    assert summary["status_label"] == "正在抽取 Memory"


def test_running_index_is_presented_as_second_stage():
    summary = summarize_build_progress(build("running", "indexing", succeeded=4, pending=0))
    assert summary["value"] == pytest.approx(0.375)
    assert summary["stage"] == 2
    assert summary["status_label"] == "正在建立检索索引"


def test_relation_tasks_advance_only_the_third_quarter():
    relation_progress = {
        "progress": {"total": 8, "succeeded": 3, "failed": 1, "pending": 4}
    }
    summary = summarize_build_progress(
        build("running", "relations", succeeded=4, pending=0), relation_progress
    )
    assert summary["value"] == pytest.approx(0.59375)
    assert summary["stage"] == 3
    assert summary["status_label"] == "正在生成历史关系"


@pytest.mark.parametrize(
    ("status", "phase", "expected"),
    [("extracted", "extraction", 0.25), ("indexed", "indexed", 0.5), ("related", "relations", 0.75), ("complete", "complete", 1.0)],
)
def test_completed_stage_boundaries(status, phase, expected):
    summary = summarize_build_progress(build(status, phase, succeeded=4, pending=0))
    assert summary["value"] == expected
