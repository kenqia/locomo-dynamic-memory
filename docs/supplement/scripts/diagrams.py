"""结构类图：F2 流水线、F3 实验谱系、F15 留出集构建恢复、F16 候选决策流。需要系统 graphviz（dot）。"""

import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "figures"
FONT = "Noto Sans CJK SC"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, VIOLET, RED, GRAY = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6", "#e34948", "#8a8985")

HEAD = f'''  graph [fontname="{FONT}", fontsize=11, bgcolor="#fcfcfb", pad=0.25, nodesep=0.28, ranksep=0.42, labeljust=l];
  node  [fontname="{FONT}", fontsize=10, shape=box, style="rounded,filled", fillcolor="#ffffff", color="#8a8985", penwidth=1.1, margin="0.12,0.06"];
  edge  [fontname="{FONT}", fontsize=8.5, color="#52514e", arrowsize=0.7];
'''


def render(name, body):
    src = OUT / f"{name}.dot"
    src.write_text("digraph G {\n" + HEAD + body + "\n}\n", encoding="utf-8")
    for fmt in ("png", "pdf"):
        args = ["dot", f"-T{fmt}", str(src), "-o", str(OUT / f"{name}.{fmt}")]
        if fmt == "png":
            args.insert(1, "-Gdpi=200")
        subprocess.run(args, check=True)
    print("wrote", name)


F2 = f'''
  rankdir=LR;
  label="图 2  系统流水线与各阶段的主要失败点（红色虚线框）"; labelloc=t; fontsize=13;
  subgraph cluster_build {{ label="构建期（每个对话一次，生成 Build 版本）"; style="rounded,dashed"; color="{GRAY}"; fontsize=10;
    src  [label="原始对话\\nSource Turn"];
    ext  [label="原子抽取\\nExtracted Memory"];
    idx  [label="混合索引\\nBM25 + MiniLM"];
    rel  [label="关系判断\\nRETAIN/UPDATE/\\nSUPERSEDE/CONFLICT"];
    cs   [label="CurrentState\\n投影（可重算）"];
    src -> ext -> idx -> rel -> cs;
  }}
  subgraph cluster_query {{ label="查询期（每道题）"; style="rounded,dashed"; color="{GRAY}"; fontsize=10;
    qa   [label="查询分析"];
    ret  [label="初始检索\\n(RRF top-20)"];
    exp  [label="相关历史扩展\\n(≤60 Memory)"];
    res  [label="有效证据解析\\n(仅 Dynamic)", fillcolor="#fde7dc", color="{ORANGE}"];
    ans  [label="回答生成\\n引用 + 解释"];
    qa -> ret -> exp -> res -> ans;
    exp -> ans [style=dashed, label="Hybrid 跳过解析", color="{BLUE}", fontcolor="{BLUE}"];
  }}
  cs -> exp [style=dotted, label="存储关系复用"];
  idx -> ret [style=dotted];
  node [shape=note, style="filled", fillcolor="#fff5f5", color="{RED}", fontsize=8.5, fontcolor="#52514e"];
  f1 [label="时间锚点契约违约\\nconv-41 / conv-44 片段反复失败\\n事实抽取遗漏（E16：5/8 例）"];
  f2 [label="未知来源 ID、同状态维度、\\n重复证据 ID 违约（E1、E24）\\n关系阶段 length 停止"];
  f3 [label="完整解析输入超预算\\n请求字节上限拒绝\\n（E12：46 项，E22：49 项）"];
  f4 [label="过度拒答、人物错绑\\n回答结构校验失败（E3、E15）"];
  f1 -> ext [color="{RED}", style=dashed, arrowhead=none];
  f2 -> rel [color="{RED}", style=dashed, arrowhead=none];
  f3 -> res [color="{RED}", style=dashed, arrowhead=none];
  f4 -> ans [color="{RED}", style=dashed, arrowhead=none];
'''

F3 = f'''
  rankdir=TB; ranksep=0.26; nodesep=0.35; newrank=true;
  label="图 3  实验谱系：每个实验由哪个观察引出（虚线为跨阶段）"; labelloc=t; fontsize=13;
  node [width=1.55];
  subgraph cluster_p1 {{ label="阶段一  10-19 至 10-21"; style="rounded,dashed"; color="{GRAY}";
    E0  [label="E0 系统构造", fillcolor="#e6f0fb"];
    E1  [label="E1 首次构建\\n关系契约系列", fillcolor="#e6f0fb"];
    E2  [label="E2 质量增量 A–E", fillcolor="#e6f0fb"];
    E3  [label="E3 10 题四策略\\n输出修复"];
    E4  [label="E4 证据覆盖\\n优化与回滚"];
    E5  [label="E5 五策略展示"];
    E0 -> E1 [label="首个真实 Build"];
    E1 -> E2 [label="172 误判 UPDATE"];
    E1 -> E3 [label="v3 Build 完成"];
    E3 -> E4 [label="证据遗漏"];
    E4 -> E5 [label="回滚后展示现状"];
  }}
  subgraph cluster_p2 {{ label="阶段二、三  10-27 至 11-03"; style="rounded,dashed"; color="{GRAY}";
    E6  [label="E6 五组机制消融"];
    E7  [label="E7 Top7"];
    E8  [label="E8 原文分块替代"];
    E9  [label="E9 Top145"];
    E10 [label="E10 Production v1", fillcolor="#fdf1d6"];
    E11 [label="E11 三轮 smoke", fillcolor="#e6f0fb"];
    E12 [label="E12 757 题全量"];
    E13 [label="E13 失败图谱\\nH/D 配对"];
    E14 [label="E14 E1/E5/E6\\n离线候选"];
    E6 -> E7 [label="conv41 抽取\\n解析违约"];
    E7 -> E8 [label="抽取是否必要"];
    E7 -> E9;
    E8 -> E10; E9 -> E10 [label="窄改动集成"];
    E10 -> E11 [label="默认预算能否跑通"];
    E11 -> E12 [label="96000 可用"];
    E12 -> E13;
    E13 -> E14 [label="D 贵且无\\n全面收益"];
  }}
  subgraph cluster_p3 {{ label="阶段四、五  11-03 至 11-05"; style="rounded,dashed"; color="{GRAY}";
    E15 [label="E15 Phase 5/6"];
    E16 [label="E16 事实审阅"];
    E17 [label="E17 D1/D2"];
    E18 [label="E18 CE 重排"];
    E19 [label="E19 Hindsight"];
    E20 [label="E20 Level A/B"];
    E21 [label="E21 有效选择"];
    E22 [label="E22 Level C v1"];
    E23 [label="E23 input v2"];
    E24 [label="E24 留出集构建", fillcolor="#e6f0fb"];
    E25 [label="E25 Level E", fillcolor="#fde7dc", penwidth=2, color="{ORANGE}"];
    E15 -> E16 [label="抽取丢事实"];
    E16 -> E17 [label="5/8 抽取遗漏"];
    E17 -> E18 [label="转检索侧"];
    E17 -> E19 [label="换后端"];
    E18 -> E20; E19 -> E20;
    E20 -> E21 [label="关系对≠\\n题内有效性"];
    E20 -> E22 [label="模块不晋级"];
    E22 -> E23 [label="49 项输入失败"];
    E23 -> E24 [label="配置锁定"];
    E24 -> E25 [label="第六份 JSON"];
  }}
  E5 -> E6 [style=dashed, constraint=false, label="raw 不占优，\\n转向机制归因"];
  E14 -> E15 [style=dashed, constraint=false, label="E6-A 进入\\n真实 canary"];
  {{ rank=same; E0; E6; E15; }}
'''

F15 = f'''
  rankdir=LR;
  label="图 15  E24 留出集 conv-43 / conv-44 的构建与恢复路径（每一步都单独授权、单独记账）"; labelloc=t; fontsize=13;
  subgraph cluster_43 {{ label="conv-43"; style="rounded,dashed"; color="{GRAY}";
    a1 [label="抽取\\n34/34 片段\\n402 Memory", fillcolor="#e6f6ef"];
    a2 [label="索引\\nMiniLM"];
    a3 [label="关系\\n400/400 任务\\n7,620 条", fillcolor="#e6f6ef"];
    a4 [label="complete\\n严格导出", fillcolor="#e6f6ef", penwidth=2, color="{AQUA}"];
    a1 -> a2 -> a3 -> a4;
  }}
  subgraph cluster_44 {{ label="conv-44"; style="rounded,dashed"; color="{GRAY}";
    b1 [label="初次抽取\\n33/34 片段\\nordinal 18 失败×3", fillcolor="#fdeaea", color="{RED}"];
    b2 [label="隔离恢复 v2\\n3 请求全部\\n时间来源违约", fillcolor="#fdeaea", color="{RED}"];
    b3 [label="successor v3\\n新 Build，1 请求成功\\n383 继承 + 9 新增", fillcolor="#e6f6ef"];
    b4 [label="关系 v1\\n374/384 成功\\n10 失败", fillcolor="#fdeaea", color="{RED}"];
    b5 [label="关系恢复 v1\\n12 请求，9 恢复\\n383/384", fillcolor="#fff6e0", color="{YELLOW}"];
    b6 [label="单任务 successor\\n1 请求成功\\n384/384，7,134 条", fillcolor="#e6f6ef"];
    b7 [label="complete\\n第六份严格 JSON", fillcolor="#e6f6ef", penwidth=2, color="{AQUA}"];
    b1 -> b2 [label="不放宽契约"];
    b2 -> b3 [label="修正时间\\n原文锚定"];
    b3 -> b4 -> b5 -> b6 -> b7;
  }}
  a4 -> e [style=invis];
  e [label="E25 Level E\\n一次性留出评测", fillcolor="#fde7dc", color="{ORANGE}", penwidth=2];
  a4 -> e; b7 -> e;
'''

F16 = f'''
  rankdir=LR; nodesep=0.12; ranksep=0.5;
  label="图 16  候选的最终去向"; labelloc=t; fontsize=13;
  node [shape=box, style="rounded,filled", fontsize=9, width=2.6];
  subgraph cluster_adopt {{ label="采用为默认"; style="rounded,filled"; fillcolor="#e6f6ef"; color="{AQUA}";
    ad1 [label="持久恢复与失败 / unknown 分母"];
    ad2 [label="来源绑定、完整输入预算保护"];
    ad3 [label="安全诊断码、受限回答反馈"];
    ad4 [label="动态关系 + 多版本 + 严格 JSON 导出"];
    ad5 [label="移除普通 Dynamic 失败后的隐式 raw 重跑"];
  }}
  subgraph cluster_opt {{ label="保留为 opt-in / 研究候选"; style="rounded,filled"; fillcolor="#e6f0fb"; color="{BLUE}";
    op1 [label="显式 reader v2（E7）"];
    op2 [label="选择性前文 + 复核，−28.3% token（E9）"];
    op3 [label="单命题抽取（E9）"];
    op4 [label="E5 编码缓存、E6-A 可逆表示（E14）"];
    op5 [label="Graph 浏览、状态来源面板（E20）"];
    op6 [label="Dynamic 作为显式可选策略（E23/E25）"];
  }}
  subgraph cluster_hold {{ label="HOLD（证据不足）"; style="rounded,filled"; fillcolor="#fff6e0"; color="{YELLOW}";
    h1 [label="E6-A 真实扩展（语义风险，E15）"];
    h2 [label="E7-A/B 来源恢复（E15）"];
    h3 [label="D1 原文锚点、D2 邻接上下文（E17）"];
    h4 [label="Cross-Encoder 重排（E18）"];
    h5 [label="Hindsight 后端（E19）"];
  }}
  subgraph cluster_rej {{ label="淘汰 / REJECT"; style="rounded,filled"; fillcolor="#fdeaea"; color="{RED}";
    r1 [label="P0/P1 证据覆盖优化，已回滚（E4）"];
    r2 [label="关闭 thinking 降本（E7）"];
    r3 [label="原文分块替代结构化链路（E8）"];
    r4 [label="首次检查替换、源内时间索引、patch（E9）"];
    r5 [label="F01 四包、F03 selective（E10）"];
    r6 [label="E1 便宜路径路由（E14）"];
    r7 [label="自适应排序（−0.029）、PropMem 直接配置（E20）"];
    r8 [label="Qwen3 0.6B + 导出器配置（E19）"];
  }}
  ad1 -> op1 -> h1 -> r1 [style=invis];
'''

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    render("f02_pipeline", F2)
    render("f03_lineage", F3)
    render("f15_holdout_recovery", F15)
    render("f16_decisions", F16)
