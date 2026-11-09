"""Generate M5 final data figures read-only from frozen E25 artifacts. No model calls."""
import hashlib, json, sys
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc']:
    if Path(f).exists(): font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': ['Noto Sans CJK SC', 'DejaVu Sans'], 'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.unicode_minus': False, 'savefig.dpi': 220})
H, D = '#4C6A92', '#C8743A'
E = ROOT / 'experiments/m5-development'
OS = json.loads((E / 'level-e-results-v1/official-scores.json').read_text())
RT = json.loads((E / 'level-e-runtime-terminal-v1.json').read_text())
AUD = json.loads((ROOT / 'experiments/evidence-flow-20261109/audit.json').read_text())
inputs = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [
    'experiments/m5-development/level-e-results-v1/official-scores.json',
    'experiments/m5-development/level-e-runtime-terminal-v1.json',
    'experiments/evidence-flow-20261109/audit.json']}

# ---- recompute from items
by = {}
for x in OS['items']: by.setdefault(x['question_id'], {})[x['arm']] = x
val = lambda x: (x['qa']['value'] or 0) if x['outcome'] == 'succeeded' else 0
q14 = [q for q in by if by[q]['dynamic']['category'] < 5]
h = np.array([val(by[q]['hybrid_no_resolution']) for q in q14]); d = np.array([val(by[q]['dynamic']) for q in q14])
diff = d - h; rng = np.random.default_rng(51104)
boot = np.mean(diff[rng.integers(0, len(diff), (2000, len(diff)))], axis=1); lo, hi = np.quantile(boot, [.025, .975])
def recall(arm, stage, k='10'):
    v = [x['source_recall'][stage][k] for x in OS['items'] if x['arm'] == arm and x['source_recall'][stage][k] is not None]
    return sum(v) / len(v) if v else None
G = RT['groups']
def g(arm, *path):
    o = G['all/' + arm]
    for p in path: o = o[p]
    return o
nums = dict(hybrid_f1=h.mean(), dynamic_f1=d.mean(), diff=diff.mean(), ci=[lo, hi], n=len(q14))

# ---- F5: F1 + CI
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.4), gridspec_kw={'width_ratios': [1.15, 1]})
bars = a1.bar(['Hybrid', 'Dynamic'], [h.mean(), d.mean()], color=[H, D], width=.55)
for b, v in zip(bars, [h.mean(), d.mean()]): a1.text(b.get_x() + b.get_width() / 2, v + .008, f'{v:.6f}', ha='center')
a1.set_ylim(0, .5); a1.set_ylabel('token F1（失败记 0）'); a1.set_title('E25 类别 1–4，每臂 301 题', fontsize=11)
a2.axvline(0, color='#888', lw=1, ls='--')
a2.errorbar([diff.mean()], [0], xerr=[[diff.mean() - lo], [hi - diff.mean()]], fmt='o', color=D, capsize=6, ms=8)
a2.text(diff.mean(), .18, f'+{diff.mean():.6f}\n95% CI [{lo:+.6f}, {hi:+.6f}]', ha='center', fontsize=10)
a2.set_yticks([]); a2.set_ylim(-.5, .6); a2.set_xlim(-.04, .05); a2.set_xlabel('Dynamic − Hybrid（按题配对 bootstrap，seed 51104×2000）')
a2.set_title('配对差：区间跨零', fontsize=11); a2.spines['left'].set_visible(False)
fig.tight_layout(); fig.savefig(OUT / 'F5_e25_f1_ci.png'); plt.close(fig)

# ---- F6: cost by operation + latency
ops = ['query_analysis', 'resolve', 'answer', 'failed_operation']; lab = ['Query Analysis', 'Resolve', 'Answer', '失败操作']
cols = ['#9AA9BF', '#C8743A', '#4C6A92', '#BBBBBB']
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.4))
for i, arm in enumerate(['hybrid_no_resolution', 'dynamic']):
    left = 0
    for op, c, l in zip(ops, cols, lab):
        v = float(g(arm, 'costs', 'by_operation', op, 'reported_usage_peak_cache_miss_upper_usd'))
        a1.barh(i, v, left=left, color=c, label=l if i == 1 else None); left += v
    tot = float(g(arm, 'costs', 'all_attempts', 'adapter_reported', 'reported_usage_peak_cache_miss_upper_usd'))
    a1.text(left + .1, i, f'USD {tot:.4f}', va='center')
a1.set_yticks([0, 1], ['Hybrid', 'Dynamic']); a1.set_xlim(0, 8.6); a1.set_xlabel('已报 usage 峰价估算，USD（非账单）')
a1.set_title('查询费用估算：Dynamic ≈ 7.90×', fontsize=11); a1.legend(fontsize=8.5, frameon=False, loc='lower right')
p50 = [float(g(a, 'elapsed_seconds', 'p50')) for a in ['hybrid_no_resolution', 'dynamic']]
p95 = [float(g(a, 'elapsed_seconds', 'p95')) for a in ['hybrid_no_resolution', 'dynamic']]
x = np.arange(2); a2.bar(x - .18, p50, .36, color=[H, D], label='p50'); a2.bar(x + .18, p95, .36, color=[H, D], alpha=.45, label='p95')
for xi, v in zip(list(x - .18) + list(x + .18), p50 + p95): a2.text(xi, v + .2, f'{v:.2f}', ha='center', fontsize=9)
a2.set_xticks(x, ['Hybrid', 'Dynamic']); a2.set_ylabel('单题耗时，秒（含失败，离线串行）'); a2.set_title('延迟：p50 ≈ 3.51×（深色 p50 / 浅色 p95）', fontsize=11)
fig.tight_layout(); fig.savefig(OUT / 'F6_e25_cost_latency.png'); plt.close(fig)

# ---- F7: two panels, two separate measures
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 3.7))
st = ['initial', 'effective', 'answer_delivered']; stl = ['initial', 'effective', 'delivered']
hv = [recall('hybrid_no_resolution', 'initial'), None, recall('hybrid_no_resolution', 'answer_delivered')]
dv = [recall('dynamic', s) for s in st]
a1.plot([0, 2], [hv[0], hv[2]], 'o-', color=H, label='Hybrid（无 effective 阶段）')
a1.plot([0, 1, 2], dv, 'o-', color=D, label='Dynamic')
for i, v in enumerate(dv): a1.text(i, v - .045, f'{v:.6f}', ha='center', color=D, fontsize=9)
for i, v in [(0, hv[0]), (2, hv[2])]: a1.text(i, v + .02, f'{v:.6f}', ha='center', color=H, fontsize=9)
a1.set_xticks(range(3), stl); a1.set_ylim(.4, .8); a1.set_ylabel('标注 Source Turn 覆盖（代理）')
a1.set_title('(a) 固定 K=10（Memory 排名）、399 可映射题、失败记 0\nexpanded 与 initial 相同，未单列', fontsize=10)
a1.legend(frameon=False, fontsize=9, loc='lower left')
s = AUD['summary']['all_memory_source_recall_successful']; k4 = ['initial', 'expanded', 'effective', 'delivered']; v4 = [s[k] for k in k4]
a2.bar(range(4), v4, color=['#9AA9BF', '#9AA9BF', D, D], width=.55)
for i, v in enumerate(v4): a2.text(i, v + .012, f'{v:.6f}', ha='center', fontsize=9)
a2.set_xticks(range(4), k4); a2.set_ylim(0, .95)
a2.set_title('(b) Dynamic 成功子集、不限 K（另一口径，不与 (a) 比较）', fontsize=10)
fig.text(.5, -.02, f"冻结 Trace 审计：{AUD['summary']['resolver_lost_gold_questions']}/400 题在解析后失去 ≥1 个标注来源（标注来源被排除，非误删判定）；"
         f"{AUD['summary']['budget_lost_gold_questions']} 题因 Answer 预算再失去。", ha='center', fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT / 'F7_evidence_loss.png', bbox_inches='tight'); plt.close(fig)

nums.update(recall_at10={'hybrid': hv, 'dynamic': dv, 'dynamic_expanded': recall('dynamic', 'expanded')}, success_subset_unbounded=v4,
            cost_usd=[float(g(a, 'costs', 'all_attempts', 'adapter_reported', 'reported_usage_peak_cache_miss_upper_usd')) for a in ['hybrid_no_resolution', 'dynamic']],
            p50=p50, p95=p95)
outs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('F*.png'))}
(OUT / 'figure-provenance.json').write_text(json.dumps({'inputs_sha256': inputs, 'outputs_sha256': outs, 'recomputed': nums,
    'matplotlib': matplotlib.__version__, 'model_calls': 0}, indent=2, default=float) + '\n')
print(json.dumps(nums, default=float))
