"""Standalone, escaped HTML reports for evaluation and experiment exports."""

from __future__ import annotations

from html import escape
import json
from typing import Any


LABELS = {
    "dynamic": "完整动态系统",
    "dynamic_raw_fallback": "Dynamic + 原文兜底",
    "full_text": "Full Text 原始轮次",
    "vector": "Vector RAG",
    "hybrid_no_resolution": "Hybrid + 扩展",
}


def _text(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value))


def _number(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        if percent:
            return f"{value * 100:.1f}%"
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return _text(value)


def _strategy_rows(run: dict[str, Any]) -> str:
    rows = []
    for strategy, summary in run.get("summary", {}).items():
        execution = summary.get("execution", {})
        qa = summary.get("qa", {})
        baseline = summary.get("baseline_run_score", {})
        rows.append(
            "<tr>"
            f"<td><strong>{_text(LABELS.get(strategy, strategy))}</strong><small>{_text(strategy)}</small></td>"
            f"<td>{_number(qa.get('mean'))}</td>"
            f"<td>{_number(execution.get('success_rate'), percent=True)}</td>"
            f"<td>{_text(execution.get('succeeded'))} / {_text(execution.get('planned'))}</td>"
            f"<td>{_number(baseline.get('value'))}</td>"
            f"<td><span class=\"status\">{_text(baseline.get('status'))}</span></td>"
            "</tr>"
        )
    return "".join(rows) or '<tr><td colspan="6" class="empty">当前运行尚无策略汇总。</td></tr>'


def _result_rows(run: dict[str, Any]) -> str:
    rows = []
    for result in run.get("results", []):
        trace = result.get("trace", {})
        answer = trace.get("answer", {})
        error = result.get("error", {})
        question = ""
        samples = run.get("input", {}).get("samples", [])
        index = result.get("sample_index")
        if isinstance(index, int) and 0 <= index < len(samples):
            question = samples[index].get("question", "")
        answer_text = answer.get("answer") or error.get("code") or "—"
        rows.append(
            "<tr>"
            f"<td>{_text(index)}</td>"
            f"<td><strong>{_text(question)}</strong><small>{_text(LABELS.get(result.get('strategy'), result.get('strategy')))}</small></td>"
            f"<td>{_number(result.get('qa', {}).get('value'))}</td>"
            f"<td><span class=\"status\">{_text(answer.get('status') or error.get('code'))}</span></td>"
            f"<td class=\"answer\">{_text(answer_text)}</td>"
            "</tr>"
        )
    return "".join(rows) or '<tr><td colspan="5" class="empty">当前运行尚无逐项结果。</td></tr>'


def _metric_card(label: str, value: Any, note: str) -> str:
    return (
        '<article class="metric">'
        f'<span>{escape(label)}</span><strong>{_text(value)}</strong><small>{escape(note)}</small>'
        "</article>"
    )


def render_evaluation_report_html(
    run: dict[str, Any], *, title: str = "动态记忆评测报告", subtitle: str | None = None
) -> str:
    """Render a self-contained report without external assets or unsafe values."""
    progress = run.get("progress", {})
    total = progress.get("total") or len(run.get("results", []))
    succeeded = progress.get("succeeded")
    if succeeded is None:
        succeeded = sum(1 for row in run.get("results", []) if not row.get("error"))
    elapsed = run.get("elapsed_seconds")
    strategy_count = len(run.get("strategies", [])) or len(run.get("summary", {}))
    status = run.get("status", "not_started")
    report_subtitle = subtitle or "固定版本、逐项结果与证据边界的可复核摘要"
    raw_summary = escape(json.dumps(run.get("overall_summary", {}), ensure_ascii=False, indent=2))
    usage = escape(json.dumps({
        "query_attempts": run.get("usage_summary", {}),
        "pinned_builds": run.get("build_usage_summary", {}),
    }, ensure_ascii=False, indent=2))
    metrics = "".join([
        _metric_card("运行状态", status, str(run.get("kind") or "evaluation")),
        _metric_card("完成项目", f"{succeeded} / {total}", "按全部计划项统计"),
        _metric_card("对照策略", strategy_count, "同一输入、固定版本"),
        _metric_card("运行耗时", f"{elapsed:.2f}s" if isinstance(elapsed, (int, float)) else "—", "不含人工复核"),
    ])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='32' fill='%23171717'/%3E%3Ctext x='32' y='39' text-anchor='middle' font-family='Arial' font-size='20' font-weight='700' fill='white'%3EDM%3C/text%3E%3C/svg%3E">
<style>
:root{{--ink:#0d0d0d;--muted:#666;--line:#e7e7e7;--panel:#f7f7f8;--accent:#10a37f;--soft:#e9f7f2}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:#fff;color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6}}
.shell{{display:grid;grid-template-columns:240px minmax(0,1fr);min-height:100vh}} aside{{position:sticky;top:0;height:100vh;padding:28px 20px;background:var(--panel);border-right:1px solid var(--line)}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:750;margin-bottom:38px}}.mark{{display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:#171717;color:#fff;font-size:12px}}
nav small{{display:block;color:#8a8a8a;font-size:10px;letter-spacing:.12em;text-transform:uppercase;margin:0 10px 10px}}nav a{{display:block;padding:9px 10px;border-radius:9px;color:#343434;text-decoration:none;font-size:13px;margin:2px 0}}nav a:hover{{background:#e9e9ea}}
.aside-note{{position:absolute;left:20px;right:20px;bottom:24px;padding:12px;border:1px solid var(--line);border-radius:12px;background:#fff;color:var(--muted);font-size:11px}}
main{{width:min(1060px,100%);padding:54px 64px 90px}}.eyebrow{{color:var(--accent);font-size:11px;font-weight:750;letter-spacing:.12em;text-transform:uppercase}}h1{{font-size:44px;letter-spacing:-.045em;line-height:1.08;margin:10px 0 12px}}.lede{{max-width:720px;color:var(--muted);margin:0 0 28px}}
.runline{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 34px}}.pill,.status{{display:inline-block;background:var(--soft);color:#08745b;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:700}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 52px}}.metric{{border:1px solid var(--line);border-radius:16px;padding:17px;background:#fff}}.metric span,.metric small{{display:block;color:var(--muted);font-size:11px}}.metric strong{{display:block;font-size:24px;letter-spacing:-.03em;margin:8px 0 2px}}
section{{scroll-margin-top:28px;margin:0 0 52px}}h2{{font-size:23px;letter-spacing:-.025em;margin:0 0 8px}}.section-note{{color:var(--muted);font-size:13px;margin:0 0 18px}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:14px}}table{{border-collapse:collapse;width:100%;font-size:12px}}th{{background:var(--panel);color:#555;text-align:left;font-size:10px;letter-spacing:.04em;text-transform:uppercase}}th,td{{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}}tr:last-child td{{border-bottom:0}}td small{{display:block;color:#888;margin-top:3px}}td.answer{{min-width:260px;max-width:440px}}.empty{{color:var(--muted);text-align:center;padding:28px}}
details{{border:1px solid var(--line);border-radius:14px;margin:10px 0;background:#fff}}summary{{cursor:pointer;padding:14px 16px;font-weight:650;font-size:13px}}pre{{white-space:pre-wrap;word-break:break-word;margin:0;padding:0 16px 18px;color:#4f4f4f;font:11px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace}}
.boundary{{padding:18px 20px;border-radius:15px;background:var(--panel);color:#444;font-size:13px}}footer{{border-top:1px solid var(--line);padding-top:18px;color:#888;font-size:11px}}
@media(max-width:820px){{.shell{{display:block}}aside{{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}}nav{{display:flex;flex-wrap:wrap}}nav small,.aside-note{{display:none}}main{{padding:34px 20px 60px}}h1{{font-size:34px}}.metrics{{grid-template-columns:repeat(2,1fr)}}}}
@media print{{aside{{display:none}}.shell{{display:block}}main{{padding:0;width:100%}}details{{break-inside:avoid}}}}
</style>
</head>
<body><div class="shell">
<aside><div class="brand"><span class="mark">DM</span><span>Dynamic Memory</span></div><nav><small>Report</small><a href="#overview">运行概览</a><a href="#strategies">策略对照</a><a href="#results">逐项结果</a><a href="#evidence">证据边界</a></nav><div class="aside-note">报告保留运行身份与统计口径。原始 Trace 以同目录 JSON 为准。</div></aside>
<main><header id="overview"><div class="eyebrow">Evaluation report</div><h1>{escape(title)}</h1><p class="lede">{escape(report_subtitle)}</p><div class="runline"><span class="pill">Run {_text(run.get('run_id'))}</span><span class="pill">{_text(status)}</span></div></header>
<div class="metrics">{metrics}</div>
<section id="strategies"><h2>策略结果</h2><p class="section-note">QA 均值仅统计成功且可计分项，运行成功率覆盖全部计划项。</p><div class="table-wrap"><table><thead><tr><th>策略</th><th>QA 均值</th><th>成功率</th><th>成功 / 计划</th><th>基线得分</th><th>状态</th></tr></thead><tbody>{_strategy_rows(run)}</tbody></table></div></section>
<section id="results"><h2>逐项结果</h2><p class="section-note">回答状态与错误码并列展示，便于快速定位待复核项目。</p><div class="table-wrap"><table><thead><tr><th>#</th><th>问题 / 策略</th><th>QA</th><th>状态</th><th>回答或错误</th></tr></thead><tbody>{_result_rows(run)}</tbody></table></div></section>
<section id="evidence"><h2>口径与证据边界</h2><div class="boundary">来源覆盖表示引用能够映射到原始轮次，不单独证明语义结论。未完成运行的最终得分保持为空，未知外部结果也不按零调用处理。</div><details><summary>总体汇总</summary><pre>{raw_summary}</pre></details><details><summary>调用与构建用量</summary><pre>{usage}</pre></details></section>
<footer>Dynamic Memory · standalone report · UTF-8</footer></main></div></body></html>"""


def render_experiment_report_html(
    state: dict[str, Any], scope: str, run: dict[str, Any] | None = None
) -> str:
    report = dict(run or {})
    report.setdefault("status", state.get("status", "not_started"))
    report.setdefault("run_id", state.get(f"{scope}_run_id"))
    description = f"{scope} 范围实验摘要，生成时间 {state.get('updated_at') or '—'}。"
    if not run and state.get("blockers"):
        description += " 当前阻塞：" + "、".join(map(str, state["blockers"])) + "。"
    return render_evaluation_report_html(
        report,
        title=f"开发集实验报告 · {scope}",
        subtitle=description,
    )
