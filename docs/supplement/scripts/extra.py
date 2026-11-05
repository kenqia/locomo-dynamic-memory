"""时间线、迭代比较、预算递进与补充数据图：F1、F13、F14、S1–S4。"""

from datetime import date

import numpy as np

from common import (
    BAD, D_COLOR, GOOD, H_COLOR, INK, INK_2, MUTED, NEUTRAL, SERIES, SURFACE,
    load, note, plt, save, setup,
)

LANES = ["构建", "评测", "诊断", "决策"]
LANE_COLOR = dict(zip(LANES, SERIES))


def _day(s):
    mm, dd = s.split("-")
    return date(2026, int(mm), int(dd)).toordinal()


def f1_timeline(m):
    rows = m["timeline"]
    fig, ax = plt.subplots(figsize=(10.5, 7.6))
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        s, e = _day(r["start"]), _day(r["end"]) + 1
        ax.barh(yi, e - s - 0.12, left=s + 0.06, height=0.62, color=LANE_COLOR[r["lane"]])
        ax.text(e + 0.15, yi, f"{r['id']}  {r['label']}", va="center", fontsize=8, color=INK)
    d0, d1 = _day("10-19"), _day("11-06")
    ticks = list(range(d0, d1 + 1, 2))
    ax.set_xticks(ticks, [date.fromordinal(t).strftime("%m-%d") for t in ticks], fontsize=8)
    ax.set_xlim(d0 - 0.3, d1 + 5.5)
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.axvspan(_day("10-22"), _day("10-27"), color="#f1f0ec", zorder=0)
    ax.text(_day("10-22") + 2.5, y[-1], "M4 交付期\n（不在本文范围）", ha="center", va="center", fontsize=8, color=MUTED)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=LANE_COLOR[l], label=l) for l in LANES],
              loc="upper right", ncols=4, bbox_to_anchor=(1.0, 1.06))
    ax.set_title("图 1  实验总时间线（2026-10-19 至 11-05）", pad=18)
    save(fig, "f01_timeline")


def f13_iterations(m):
    it = m["iteration_pairs"]
    rows = it["rows"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.2), gridspec_kw={"width_ratios": [2.3, 1]})
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        b = r["before"][0] / r["before"][1]
        a = r["after"][0] / r["after"][1]
        col = GOOD if r["kept"] else (BAD if a < b else MUTED)
        a1.plot([b, a], [yi, yi], color=col, lw=2, zorder=1)
        a1.plot(b, yi, "o", color=SURFACE, mec=INK_2, mew=1.5, ms=7, zorder=2)
        a1.plot(a, yi, "o", color=col, mec=SURFACE, mew=1.2, ms=8, zorder=3)
        a1.text(1.03, yi, f"{r['before'][0]}/{r['before'][1]} → {r['after'][0]}/{r['after'][1]}",
                transform=a1.get_yaxis_transform(), va="center", fontsize=7.5, color=INK_2)
    a1.set_yticks(y, [r["label"] for r in rows], fontsize=8)
    a1.set_xlim(0, 1.05)
    a1.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    a1.grid(axis="y", visible=False)
    a1.set_title("(a) 对照（空心）→ 候选（实心）", fontsize=10)
    a1.plot([], [], "o", color=GOOD, label="保留为候选")
    a1.plot([], [], "o", color=BAD, label="淘汰：变差")
    a1.plot([], [], "o", color=MUTED, label="淘汰：无改善或另有缺陷")
    a1.legend(loc="lower left", bbox_to_anchor=(0, -0.32), ncols=3, fontsize=8)
    t = it["tokens"]
    bars = a2.bar([x["label"].replace(" + ", "\n+ ") for x in t], [x["tokens"] for x in t],
                  color=[NEUTRAL, GOOD], width=0.55)
    for b in bars:
        a2.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.01, f"{int(b.get_height()):,}", ha="center", fontsize=8)
    a2.set_ylabel("4 道已知题 × 2 次的 pipeline tokens")
    a2.grid(axis="x", visible=False)
    a2.set_title("(b) E9 同质量（8/8）下的 token", fontsize=10)
    a2.set_ylim(0, 135000)
    a2.annotate("−28.3%", xy=(1, 80000), xytext=(0.5, 122000), ha="center", fontsize=11,
                fontweight="bold", color=INK, arrowprops=dict(arrowstyle="->", color=INK_2))
    fig.suptitle("图 13  E7–E9 迭代：候选与对照的同题比较", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    note(a1, "样本均为已曝光开发题，单位各不相同（题、事实、输出）；只在同一行内比较。")
    save(fig, "f13_iterations")


def f14_budget(m):
    rows = m["budget_progression"]["rows"]
    fig, ax = plt.subplots(figsize=(11.0, 4.2))
    x = np.arange(len(rows))
    rate = [r["D_ok"] / r["D_n"] for r in rows]
    ax.plot(x, rate, "-", color=D_COLOR, lw=2, zorder=1)
    ax.plot(x, rate, "o", color=D_COLOR, ms=9, mec=SURFACE, mew=1.5, zorder=2)
    for xi, r, v in zip(x, rows, rate):
        ax.text(xi, v + 0.06, f"{r['D_ok']}/{r['D_n']}", ha="center", fontsize=8.5, color=INK)
        ax.text(xi, -0.24, r["note"].replace("，", "，\n"), ha="center", va="top", fontsize=7, color=MUTED,
                transform=ax.get_xaxis_transform())
    ax.set_xticks(x, [r["label"] for r in rows], fontsize=8)
    ax.set_ylim(-0.05, 1.18)
    ax.set_xlim(-0.5, len(rows) - 0.5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylabel("Dynamic 运行成功率")
    ax.grid(axis="x", visible=False)
    ax.set_title("图 14  输入/输出预算递进与 Dynamic 运行成功率")
    fig.tight_layout()
    save(fig, "f14_budget")


def s1_showcase(m):
    s = m["showcase_e5"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.4, 3.3), gridspec_kw={"width_ratios": [1.6, 1]})
    cols = [NEUTRAL, SERIES[2], H_COLOR, D_COLOR, SERIES[3]]
    bars = a1.bar(s["strategies"], s["f1"], color=cols, width=0.6)
    for b in bars:
        a1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.008, f"{b.get_height():.3f}", ha="center", fontsize=8)
    a1.set_ylim(0, 0.6)
    a1.set_ylabel("F1，16 道可回答题")
    a1.grid(axis="x", visible=False)
    a1.set_title("(a) 五策略 QA", fontsize=10)
    ks = list(s["recall_at"])
    vals = list(s["recall_at"].values())
    a2.plot([int(k) for k in ks], vals, "-o", color=H_COLOR, lw=2, ms=7)
    for k, v in zip(ks, vals):
        a2.text(int(k), v + 0.012, f"{v:.3f}", ha="center", fontsize=8)
    a2.set_xticks([5, 10, 20])
    a2.set_ylim(0.55, 0.85)
    a2.set_xlabel("K（Memory 排名）")
    a2.set_title("(b) 初始检索 Recall@K，40 题", fontsize=10)
    fig.suptitle("补充图 S1  E5 现状展示（conv-26，已曝光开发题）", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    save(fig, "s1_showcase")


def s2_source_review(m):
    rows = m["source_review_e25"]["rows"]
    fig, ax = plt.subplots(figsize=(8.8, 3.9))
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        h = r["H"][0] / r["H"][1]
        d = r["D"][0] / r["D"][1]
        ax.plot([h, d], [yi, yi], color=NEUTRAL, lw=3, zorder=1)
        ax.plot(h, yi, "o", color=H_COLOR, ms=8, mec=SURFACE, mew=1.5, zorder=2)
        ax.plot(d, yi, "o", color=D_COLOR, ms=8, mec=SURFACE, mew=1.5, zorder=2)
        ax.text(1.02, yi, f"H {r['H'][0]}/{r['H'][1]}   D {r['D'][0]}/{r['D'][1]}",
                transform=ax.get_yaxis_transform(), va="center", fontsize=7.5, color=INK_2)
    ax.axhline(3.5, color=MUTED, lw=0.6, ls=":")
    ax.text(0.01, 3.62, "↑ 越高越好", transform=ax.get_yaxis_transform(), fontsize=7.5, color=MUTED)
    ax.text(0.01, 3.2, "↓ 错误率，越低越好", transform=ax.get_yaxis_transform(), fontsize=7.5, color=MUTED)
    ax.set_yticks(y, [r["label"] for r in rows])
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(axis="y", visible=False)
    ax.plot([], [], "o", color=H_COLOR, label="Hybrid")
    ax.plot([], [], "o", color=D_COLOR, label="Dynamic")
    ax.legend(loc="lower right")
    ax.set_title("补充图 S2  E25 留出集 800 项来源盲审（各行分母不同）")
    fig.tight_layout()
    note(ax, "分母只含运行成功且标签适用的单位；每项仅一名非作者 AI 审阅，不是人工或教师真值。")
    save(fig, "s2_source_review")


def s3_e7_hits(m):
    rows = m["e7a_hits"]["rows"]
    x = np.arange(len(rows))
    w = 0.26
    fig, ax = plt.subplots(figsize=(8.2, 3.4))
    for i, (key, lab, col) in enumerate([("base", "Baseline", NEUTRAL), ("A", "E7-A", SERIES[2]), ("AB", "E7-A+B", SERIES[5])]):
        vals = [r[key] / r["n"] for r in rows]
        bars = ax.bar(x + (i - 1) * (w + 0.02), vals, w, color=col, label=lab)
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.005, f"{b.get_height():.1%}", ha="center", fontsize=7)
    ax.set_xticks(x, [f"{r['conv']}\n{r['n']} 个来源题次" for r in rows], fontsize=8.5)
    ax.set_ylim(0.6, 0.92)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", ncols=3)
    ax.set_title("补充图 S3  E15 Phase 6 E7 离线：标注来源命中率")
    fig.tight_layout()
    note(ax, "命中只表示参考 Source ID 出现在候选中，不是事实召回或 QA 改善；含对抗题诱导来源。")
    save(fig, "s3_e7_hits")


def s4_ce_category(m):
    rows = m["ce_by_category_e18"]["rows"]
    overall = {"cat": "全部 753 题", "n": 753, "d": -0.009790}
    rows = rows + [overall]
    fig, ax = plt.subplots(figsize=(7.4, 2.8))
    y = np.arange(len(rows))[::-1]
    cols = [GOOD if r["d"] > 0 else BAD for r in rows]
    cols[-1] = MUTED
    bars = ax.barh(y, [r["d"] for r in rows], color=cols, height=0.55)
    for b, r in zip(bars, rows):
        xpos = b.get_width() + (0.003 if r["d"] > 0 else -0.003)
        ax.text(xpos, b.get_y() + b.get_height() / 2, f"{r['d']:+.4f}", va="center",
                ha="left" if r["d"] > 0 else "right", fontsize=8)
    ax.axvline(0, color=INK, lw=0.9)
    ax.set_yticks(y, [f"{r['cat']}（{r['n']}）" for r in rows])
    ax.set_xlim(-0.04, 0.09)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("交付 Recall 配对差 C1−C0")
    ax.set_title("补充图 S4  E18 Cross-Encoder 重排的类别差异")
    fig.tight_layout()
    note(ax, "类别 4/5 未单列；总体为负且区间跨零，类别差异未作多重比较校正。")
    save(fig, "s4_ce_category")


if __name__ == "__main__":
    setup()
    m = load()
    for f in [f1_timeline, f13_iterations, f14_budget, s1_showcase, s2_source_review, s3_e7_hits, s4_ce_category]:
        f(m)
