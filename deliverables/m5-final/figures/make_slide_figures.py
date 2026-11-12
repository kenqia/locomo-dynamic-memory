"""Slide-sized versions of F5/F6/F7(a): same frozen inputs, larger fonts, plain labels."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
ROOT, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc']: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': ['Noto Sans CJK SC'], 'font.size': 15, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.unicode_minus': False, 'savefig.dpi': 220})
H, D = '#4C6A92', '#C8743A'
E = ROOT / 'experiments/m5-development'
OS = json.loads((E / 'level-e-results-v1/official-scores.json').read_text()); RT = json.loads((E / 'level-e-runtime-terminal-v1.json').read_text())
by = {}
for x in OS['items']: by.setdefault(x['question_id'], {})[x['arm']] = x
val = lambda x: (x['qa']['value'] or 0) if x['outcome'] == 'succeeded' else 0
qs = [q for q in by if by[q]['dynamic']['category'] < 5]
h = np.array([val(by[q]['hybrid_no_resolution']) for q in qs]); d = np.array([val(by[q]['dynamic']) for q in qs]); df = d - h
bs = np.mean(df[np.random.default_rng(51104).integers(0, len(df), (2000, len(df)))], axis=1); lo, hi = np.quantile(bs, [.025, .975])
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={'width_ratios': [1, 1.2]})
br = a.bar(['Hybrid', 'Dynamic'], [h.mean(), d.mean()], color=[H, D], width=.55)
for r, v in zip(br, [h.mean(), d.mean()]): a.text(r.get_x() + r.get_width()/2, v + .01, f'{v:.3f}', ha='center', fontsize=16, fontweight='bold')
a.set_ylim(0, .5); a.set_title('事实类 token F1', fontsize=16)
b.axvline(0, color='#888', ls='--'); b.errorbar([df.mean()], [0], xerr=[[df.mean()-lo], [hi-df.mean()]], fmt='o', color=D, capsize=8, ms=10, lw=2.5)
b.text(df.mean(), .22, f'+{df.mean():.3f}  [{lo:+.3f}, {hi:+.3f}]', ha='center', fontsize=15)
b.set_yticks([]); b.set_ylim(-.5, .6); b.set_xlim(-.04, .05); b.spines['left'].set_visible(False); b.set_title('Dynamic − Hybrid 的 95% 区间跨零', fontsize=16)
fig.tight_layout(); fig.savefig(OUT / 'S5_f1.png'); plt.close(fig)
G = RT['groups']; g = lambda arm, *p: (lambda o: [o := o[k] for k in p][-1])(G['all/' + arm])
cost = [float(g(a_, 'costs', 'all_attempts', 'adapter_reported', 'reported_usage_peak_cache_miss_upper_usd')) for a_ in ['hybrid_no_resolution', 'dynamic']]
res = float(g('dynamic', 'costs', 'by_operation', 'resolve', 'reported_usage_peak_cache_miss_upper_usd'))
p50 = [float(g(a_, 'elapsed_seconds', 'p50')) for a_ in ['hybrid_no_resolution', 'dynamic']]
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.4))
a.barh([1], [cost[1] - res], left=[res], color='#4C6A92'); a.barh([1], [res], color=D, label='解析步骤'); a.barh([0], [cost[0]], color=H)
for y, v in zip([0, 1], cost): a.text(v + .15, y, f'${v:.2f}', va='center', fontsize=16, fontweight='bold')
a.set_yticks([0, 1], ['Hybrid', 'Dynamic']); a.set_xlim(0, 8.5); a.set_title('估算查询费用（美元，非账单）', fontsize=16); a.legend(frameon=False, fontsize=13, loc='lower right')
br = b.bar(['Hybrid', 'Dynamic'], p50, color=[H, D], width=.55)
for r, v in zip(br, p50): b.text(r.get_x() + r.get_width()/2, v + .2, f'{v:.2f} 秒', ha='center', fontsize=16, fontweight='bold')
b.set_ylim(0, 10); b.set_title('单题耗时中位数', fontsize=16)
fig.tight_layout(); fig.savefig(OUT / 'S6_cost_latency.png'); plt.close(fig)
rec = lambda arm, st: (lambda v: sum(v)/len(v))([x['source_recall'][st]['10'] for x in OS['items'] if x['arm'] == arm and x['source_recall'][st]['10'] is not None])
hv = [rec('hybrid_no_resolution', 'initial'), rec('hybrid_no_resolution', 'answer_delivered')]; dv = [rec('dynamic', s) for s in ['initial', 'effective', 'answer_delivered']]
fig, a = plt.subplots(figsize=(8.6, 3.6))
a.plot([0, 2], hv, 'o-', color=H, lw=3, ms=10, label='Hybrid'); a.plot([0, 1, 2], dv, 'o-', color=D, lw=3, ms=10, label='Dynamic')
a.text(2.05, hv[1], f'{hv[1]:.2f}', va='center', color=H, fontsize=16, fontweight='bold'); a.text(2.05, dv[2], f'{dv[2]:.2f}', va='center', color=D, fontsize=16, fontweight='bold')
a.text(-.05, dv[0] + .03, f'{dv[0]:.2f}', ha='right', color=D, fontsize=15)
a.set_xticks([0, 1, 2], ['初始检索', '解析后', '送达回答']); a.set_xlim(-.3, 2.35); a.set_ylim(.4, .8)
a.set_title('前 10 条记忆覆盖的标注来源比例（400 题，失败记 0）', fontsize=15); a.legend(frameon=False, loc='lower left')
fig.tight_layout(); fig.savefig(OUT / 'S7_evidence.png'); plt.close(fig)
print(round(h.mean(),6), round(d.mean(),6), round(lo,6), round(hi,6), cost, p50, hv, dv)
