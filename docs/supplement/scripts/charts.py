"""数据类图表：F4–F14 及补充图。运行：uv run --with matplotlib python docs/supplement/scripts/charts.py"""

import numpy as np

from common import (
    BAD, D_COLOR, GOOD, H_COLOR, INK, INK_2, MUTED, NEUTRAL, SERIES, SURFACE,
    load, note, plt, save, setup,
)


def bar_labels(ax, bars, fmt="{:.3f}", dy=0.006):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + dy, fmt.format(h),
                ha="center", va="bottom", fontsize=7.5, color=INK_2)


def f4_f1_by_stage(m):
    rows = m["f1_by_stage"]["rows"]
    x = np.arange(len(rows))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    bh = ax.bar(x - w / 2 - 0.01, [r["H"] for r in rows], w, color=H_COLOR, label="Hybrid")
    bd = ax.bar(x + w / 2 + 0.01, [r["D"] for r in rows], w, color=D_COLOR, label="Dynamic")
    bar_labels(ax, bh)
    bar_labels(ax, bd)
    ax.set_xticks(x, [r["label"] for r in rows], fontsize=8.5)
    ax.set_ylim(0, 0.62)
    ax.set_ylabel("完整分母 F1（失败记零）")
    ax.grid(axis="x", visible=False)
    ax.axvspan(1.5, 4.5, color="#f1f0ec", zorder=0)
    ax.text(3, 0.595, "M5 冻结后的三次真实实验（同一 Prompt 血缘内部可比）",
            ha="center", fontsize=8, color=INK_2)
    ax.legend(loc="upper left", ncols=2)
    ax.set_title("图 4  各阶段 Hybrid 与 Dynamic 的 QA F1")
    note(ax, "注：不同实验的样本、模型配置与 thinking 血缘不同，柱高不能跨实验相减。"
             "E5 为成功项均值；E12 Hybrid 含 1 个 unknown，取下界。", y=-0.2)
    save(fig, "f04_f1_by_stage")


def f5_paired(m):
    rows = m["paired_wlt"]["rows"][::-1]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    y = np.arange(len(rows))
    tot = np.array([r["up"] + r["down"] + r["tie"] for r in rows], float)
    up = np.array([r["up"] for r in rows]) / tot
    dn = np.array([r["down"] for r in rows]) / tot
    tie = np.array([r["tie"] for r in rows]) / tot
    kw = dict(height=0.62, edgecolor=SURFACE, linewidth=1.5)
    ax.barh(y, up, color=GOOD, label="Dynamic 提升", **kw)
    ax.barh(y, tie, left=up, color=NEUTRAL, label="不变", **kw)
    ax.barh(y, dn, left=up + tie, color=BAD, label="Dynamic 退化", **kw)
    for i, r in enumerate(rows):
        ax.text(1.01, i, f"{r['up']} / {r['down']} / {r['tie']}", va="center", fontsize=8, color=INK_2)
    ax.set_yticks(y, [r["label"] for r in rows])
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, 1.0), ncols=3)
    ax.set_title("图 5  逐题配对：Dynamic 相对 Hybrid 的提升 / 退化 / 不变", pad=24)
    ax.text(1.01, len(rows) - 0.35, "升 / 降 / 平", fontsize=8, color=MUTED)
    save(fig, "f05_paired_wlt")


def _forest(ax, rows, title):
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        crosses = r["lo"] <= 0 <= r["hi"]
        c = MUTED if crosses else (GOOD if r["d"] > 0 else BAD)
        ax.plot([r["lo"], r["hi"]], [yi, yi], color=c, lw=2, solid_capstyle="round")
        ax.plot(r["d"], yi, "o", ms=7, color=c, mec=SURFACE, mew=1.5)
        ax.text(1.02, yi, f"{r['d']:+.3f}  [{r['lo']:+.3f}, {r['hi']:+.3f}]",
                transform=ax.get_yaxis_transform(), va="center", fontsize=7.5, color=INK_2)
    ax.axvline(0, color=INK, lw=0.9)
    ax.set_yticks(y, [r["label"] for r in rows], fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_title(title, fontsize=10.5)


def f6_forest(m):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.4, 6.4), gridspec_kw={"hspace": 0.45})
    fig.subplots_adjust(right=0.74)
    _forest(a1, m["forest"]["answer_f1"], "(a) 答案指标，D−H")
    a1.set_xlim(-0.40, 0.30)
    _forest(a2, m["forest"]["source_review"], "(b) 来源审阅与检索代理")
    a2.set_xlim(-0.05, 0.09)
    fig.suptitle("图 6  配对差值与 95% bootstrap 区间", x=0.02, ha="left", fontsize=12, fontweight="bold")
    note(a2, "灰色：区间跨零或触零；红/绿：区间不含零。区间仅描述所选对话内的题目不确定性，"
             "不代表跨对话泛化；多指标未作多重比较校正。", y=-0.16)
    save(fig, "f06_forest")


def f7_success(m):
    rows = m["success"]["rows"]
    x = np.arange(len(rows))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9.0, 3.6))
    for off, key, col, lab in [(-w / 2 - 0.01, "H", H_COLOR, "Hybrid"), (w / 2 + 0.01, "D", D_COLOR, "Dynamic")]:
        vals = [r[key][0] / r[key][1] for r in rows]
        bars = ax.bar(x + off, vals, w, color=col, label=lab)
        for b, r in zip(bars, rows):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015,
                    f"{r[key][0]}/{r[key][1]}", ha="center", fontsize=7, color=INK_2)
    ax.set_xticks(x, [r["label"] for r in rows], fontsize=8.5)
    ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncols=2)
    ax.set_title("图 7  运行成功率与完整分母", pad=22)
    note(ax, "失败项一律保留在分母内、记零，不补跑、不剔除。", y=-0.16)
    save(fig, "f07_success")


def f8_failures(m):
    groups = m["failures"]["groups"]
    fig, axes = plt.subplots(len(groups), 1, figsize=(8.2, 0.78 * len(groups) + 1.0))
    for ax, g in zip(axes, groups):
        items = g["items"]
        tot = sum(items.values())
        left = 0
        for i, (k, v) in enumerate(items.items()):
            col = SERIES[i % len(SERIES)]
            ax.barh(0, v / tot, left=left, color=col, edgecolor=SURFACE, linewidth=1.5, height=0.7)
            if v / tot > 0.07:
                ax.text(left + v / tot / 2, 0, f"{k} {v}", ha="center", va="center", fontsize=7.5, color=INK)
            elif v:
                ax.text(left + v / tot + 0.005, 0.0, f"{k} {v}", va="center", fontsize=7.5, color=INK_2)
            left += v / tot
        ax.set_xlim(0, 1)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title(g["exp"], fontsize=9, fontweight="normal", color=INK_2, loc="left", pad=2)
    fig.suptitle("图 8  主要失败类型的构成", x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    save(fig, "f08_failures")


def f9_funnel(m):
    r = m["recall_funnel_e25"]
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.6), sharey=True)
    for ax, ki, K in zip(axes, range(3), r["K"]):
        ax.plot([0, 1, 3], [r["H"][s][ki] for s in ["initial", "expanded", "delivered"]],
                "-o", color=H_COLOR, lw=2, ms=6, label="Hybrid（无解析阶段）")
        ax.plot([0, 1, 2, 3], [r["D"][s][ki] for s in ["initial", "expanded", "effective", "delivered"]],
                "-o", color=D_COLOR, lw=2, ms=6, label="Dynamic")
        ax.set_xticks(range(4), ["初始", "扩展", "解析", "交付"])
        ax.set_xlim(-0.3, 3.9)
        ax.set_title(f"Recall@{K}", fontsize=10)
        ax.set_ylim(0.45, 0.78)
        for key, col in [("H", H_COLOR), ("D", D_COLOR)]:
            v = r[key]["delivered"][ki]
            ax.text(3.12, v, f"{v:.3f}", fontsize=7.5, color=col, va="center")
    axes[0].set_ylabel("标注来源覆盖（代理）")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("图 9  E25 留出集：来源覆盖在流水线各阶段的变化", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    note(axes[0], "Dynamic 的有效证据解析使标注来源覆盖下降约 0.08–0.19；被删来源是否确实不适用于问题，未单独测量。")
    save(fig, "f09_recall_funnel")


def f10_attribution(m):
    a = m["attribution_e16"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 3.2))
    for ax, key, title in [(a1, "source_chain_35", "(a) 共同遗漏来源链，35 个来源题次"),
                           (a2, "confirmed_8", "(b) 8 个双审错误拒答，逐例确认")]:
        items = list(a[key].items())
        ys = np.arange(len(items))[::-1]
        bars = ax.barh(ys, [v for _, v in items], color=[SERIES[i] for i in range(len(items))], height=0.6)
        for b, (_, v) in zip(bars, items):
            ax.text(b.get_width() + 0.2, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=8.5)
        ax.set_yticks(ys, [k for k, _ in items], fontsize=8.5)
        ax.grid(axis="y", visible=False)
        ax.set_title(title, fontsize=10)
    fig.suptitle("图 10  E16 证据损失的阶段归因", x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    note(a1, "(a) 的单位是来源题次，不是独立事实；(b) 中部分案例存在阶段重叠，不能排他归因。", y=-0.16)
    save(fig, "f10_attribution")


def f11_cost(m):
    rows = m["cost_ratio"]["rows"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.3), gridspec_kw={"width_ratios": [1.5, 1]})
    y = np.arange(len(rows))[::-1]
    ratios = [r["D"] / r["H"] for r in rows]
    bars = a1.barh(y, ratios, color=D_COLOR, height=0.55)
    for b, rt in zip(bars, ratios):
        a1.text(b.get_width() + 0.15, b.get_y() + b.get_height() / 2, f"{rt:.2f}×", va="center", fontsize=8.5)
    a1.axvline(1, color=INK, lw=0.9)
    a1.set_yticks(y, [r["label"] for r in rows], fontsize=8.5)
    a1.set_xlim(0, 12)
    a1.set_xlabel("Dynamic / Hybrid 查询费用倍数")
    a1.grid(axis="y", visible=False)
    a1.set_title("(a) 查询费用倍数", fontsize=10)
    e25 = rows[-1]
    b2 = a2.bar(["Hybrid", "Dynamic"], [e25["H"], e25["D"]], color=[H_COLOR, D_COLOR], width=0.55)
    for b in b2:
        a2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.1, f"${b.get_height():.2f}", ha="center", fontsize=8.5)
    a2.set_ylabel("USD，已报 usage 峰价")
    a2.grid(axis="x", visible=False)
    a2.set_title("(b) E25 留出 400 题查询费用", fontsize=10)
    fig.suptitle("图 11  查询成本", x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    note(a1, "均按 provider 报告 usage 与峰时 cache-miss 单价折算，不是实际账单；不含 Build 费用。", y=-0.2)
    save(fig, "f11_cost")


def f12_latency(m):
    rows = m["latency"]["rows"]
    x = np.arange(len(rows))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 3.5))
    for off, key, col, lab in [(-w / 2 - 0.01, "H", H_COLOR, "Hybrid"), (w / 2 + 0.01, "D", D_COLOR, "Dynamic")]:
        p50 = [r[key][0] for r in rows]
        p95 = [r[key][1] for r in rows]
        ax.bar(x + off, p50, w, color=col, label=f"{lab} p50")
        ax.vlines(x + off, p50, p95, color=col, lw=2)
        ax.plot(x + off, p95, "_", color=col, ms=12, mew=2)
        for xi, v in zip(x + off, p95):
            ax.text(xi, v + 0.6, f"{v:.1f}", ha="center", fontsize=7.5, color=INK_2)
    ax.set_xticks(x, [r["label"] for r in rows])
    ax.set_ylabel("单题耗时，秒")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right")
    ax.set_title("图 12  单题延迟：柱为 p50，竖线顶端为 p95")
    note(ax, "串行实验、共享工作站测量，包含失败项；不作为服务吞吐承诺。", y=-0.14)
    save(fig, "f12_latency")


if __name__ == "__main__":
    setup()
    m = load()
    for f in [f4_f1_by_stage, f5_paired, f6_forest, f7_success, f8_failures, f9_funnel,
              f10_attribution, f11_cost, f12_latency]:
        f(m)
