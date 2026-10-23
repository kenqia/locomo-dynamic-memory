"""Presentation helpers for the four-stage memory build workflow."""

from __future__ import annotations

from typing import Any


STAGE_LABELS = {
    "extraction": "Memory 抽取",
    "indexing": "检索索引",
    "relations": "历史关系",
    "complete": "版本发布",
}


def _ratio(progress: dict[str, Any] | None) -> float:
    if not progress:
        return 0.0
    total = int(progress.get("total", 0))
    if total <= 0:
        return 0.0
    succeeded = int(progress.get("succeeded", 0))
    return min(max(succeeded / total, 0.0), 1.0)


def summarize_build_progress(
    build: dict[str, Any], relation_progress: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return an overall percentage and stage-aware labels for a build."""

    status = str(build["status"])
    phase = str(build["phase"])

    if status == "complete":
        return {"value": 1.0, "stage": 4, "label": "版本已发布", "status_label": "完整版本已发布"}

    if phase == "relations" or status in {"related", "relations_failed"}:
        if status == "related":
            return {"value": 0.75, "stage": 3, "label": "历史关系已生成", "status_label": "关系与当前状态已生成"}
        relation_ratio = _ratio(relation_progress.get("progress") if relation_progress else None)
        value = 0.5 + 0.25 * relation_ratio
        labels = {
            "queued": "等待生成历史关系",
            "running": "正在生成历史关系",
            "relations_failed": "历史关系生成失败",
            "interrupted": "历史关系生成中断",
        }
        return {
            "value": value,
            "stage": 3,
            "label": labels.get(status, "生成历史关系"),
            "status_label": labels.get(status, "生成历史关系"),
        }

    if phase in {"indexing", "indexed"} or status in {"indexed", "index_failed"}:
        if status == "indexed":
            return {"value": 0.5, "stage": 2, "label": "检索索引已建立", "status_label": "检索索引已建立"}
        labels = {
            "running": "正在建立检索索引",
            "index_failed": "检索索引建立失败",
            "interrupted": "检索索引建立中断",
        }
        return {
            "value": 0.375 if status == "running" else 0.25,
            "stage": 2,
            "label": labels.get(status, "等待建立检索索引"),
            "status_label": labels.get(status, "等待建立检索索引"),
        }

    extraction_ratio = _ratio(build.get("progress"))
    labels = {
        "queued": "等待抽取 Memory",
        "running": "正在抽取 Memory",
        "failed": "Memory 抽取失败",
        "interrupted": "Memory 抽取中断",
        "extracted": "Memory 已生成",
    }
    return {
        "value": 0.25 if status == "extracted" else 0.25 * extraction_ratio,
        "stage": 1,
        "label": labels.get(status, "抽取 Memory"),
        "status_label": labels.get(status, "抽取 Memory"),
    }
