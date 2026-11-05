"""补充材料图表的共用设置：数据读取、字体、调色板与保存。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "metrics.json"
OUT = ROOT / "figures"

# 参考调色板（已用 dataviz 校验器验证相邻对 CVD 与常规视觉间隔）。
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8985"
GRID = "#e4e3df"
H_COLOR = "#2a78d6"  # Hybrid，类别槽 1
D_COLOR = "#eb6834"  # Dynamic，类别槽 2
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GOOD = "#1baf7a"
BAD = "#e34948"
NEUTRAL = "#c9c8c3"


def _pick_cjk_font():
    wanted = ["Noto Sans CJK SC", "Noto Sans CJK HK", "Droid Sans Fallback", "AR PL UMing CN"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in wanted:
        if name in available:
            return name
    raise RuntimeError("未找到中文字体")


def setup():
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [_pick_cjk_font(), "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "font.size": 9.5,
            "legend.frameon": False,
            "figure.dpi": 110,
        }
    )
    OUT.mkdir(parents=True, exist_ok=True)


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def note(ax, text, y=None):
    """图注放在整张图的底部，避免和坐标轴标签重叠；y 参数保留以兼容旧调用。"""
    ax.figure.text(0.01, -0.01, text, fontsize=8, color=MUTED, va="top", ha="left")
