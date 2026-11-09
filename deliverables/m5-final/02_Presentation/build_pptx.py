"""Build the 10-slide final presentation (ZJU-blue template style of the 11-08 deck). Editable PPTX."""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

M5 = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve()
FIG = M5 / 'figures'; SHOT = M5 / 'screenshots/loaded'; LOGO = M5 / '02_Presentation/assets/zju_emblem_white.png'
BLUE, DARK, GREY, LINE, PALE, TEAL, ORANGE = (RGBColor(0x0D,0x47,0x8C), RGBColor(0x1C,0x2D,0x42), RGBColor(0x53,0x67,0x7F),
    RGBColor(0xCE,0xDA,0xEA), RGBColor(0xF1,0xF6,0xFC), RGBColor(0x00,0x88,0x91), RGBColor(0xC8,0x74,0x3A))
import os
FONT = os.environ.get('DECK_FONT', 'Microsoft YaHei')
from pptx.oxml.ns import qn
NAV = ['问题', '设计', '系统', '实验', '发现', '总结']
SECTION = {1: None, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 3, 8: 3, 9: 4, 10: 5}

prs = Presentation(); prs.slide_width, prs.slide_height = Inches(16.667), Inches(9.375)
W = 16.667

def box(sl, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None: s.fill.background()
    else: s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None: s.line.fill.background()
    else: s.line.color.rgb = line; s.line.width = Pt(1)
    s.shadow.inherit = False
    return s

def text(sl, x, y, w, h, t, size=18, color=DARK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.15):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor; tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02)
    lines = t if isinstance(t, list) else [t]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align; p.line_spacing = spacing
        segs = ln if isinstance(ln, list) else [(ln, {})]
        for seg in segs:
            s, o = (seg, {}) if isinstance(seg, str) else seg
            r = p.add_run(); r.text = s; f = r.font; f.name = FONT; f.size = Pt(o.get('size', size)); f.bold = o.get('bold', bold)
            f.color.rgb = o.get('color', color)
            rPr = r._r.get_or_add_rPr()
            for tagname in ('a:ea', 'a:cs'):
                el = rPr.find(qn(tagname))
                if el is None: el = rPr.makeelement(qn(tagname), {}); rPr.append(el)
                el.set('typeface', FONT)
    return tb

def frame(n, title):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    box(sl, 0, 0, W, 0.92, BLUE)
    text(sl, 0.42, 0.24, 0.7, 0.45, f'{n:02d}', 16.5, RGBColor(255,255,255), True)
    text(sl, 1.38, 0.2, 8.6, 0.55, title, 25, RGBColor(255,255,255), True)
    sec = SECTION[n]
    for i, lab in enumerate(NAV):
        x = 9.9 + i * 0.95
        text(sl, x, 0.28, 0.85, 0.38, lab, 12, RGBColor(255,255,255) if i == sec else RGBColor(0xAC,0xC7,0xE5), i == sec, PP_ALIGN.CENTER)
        if i == sec: box(sl, x + 0.2, 0.71, 0.45, 0.035, RGBColor(255,255,255))
    sl.shapes.add_picture(str(LOGO), Inches(15.98), Inches(0.18), Inches(0.54), Inches(0.54))
    box(sl, 1.0, 8.77, 14.67, 0.02, LINE)
    text(sl, 1.0, 8.86, 8, 0.3, 'LoCoMo Dynamic Memory · 第三组 在阴雨天游泳', 9, GREY)
    text(sl, 11.0, 8.86, 3.8, 0.3, 'M5 Final · 2026.11.09', 9, GREY, align=PP_ALIGN.RIGHT)
    text(sl, 15.1, 8.86, 0.55, 0.3, f'{n:02d}', 9, BLUE, True, PP_ALIGN.RIGHT)
    return sl

def headline(sl, main, sub=None):
    text(sl, 1.0, 1.32, 14.67, 0.7, main, 30, DARK, True)
    if sub: text(sl, 1.0, 2.05, 14.67, 0.45, sub, 17, GREY)

def pic(sl, path, x, y, w=None, h=None, border=False):
    p = sl.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)
    if border: p.line.color.rgb = LINE; p.line.width = Pt(1)
    return p

def card(sl, x, y, w, h, title, body, tcolor=BLUE, tsize=20, bsize=16):
    box(sl, x, y, w, h, PALE, LINE)
    text(sl, x + 0.28, y + 0.22, w - 0.5, 0.5, title, tsize, tcolor, True)
    text(sl, x + 0.28, y + 0.82, w - 0.5, h - 1.0, body, bsize, DARK, spacing=1.3)

def tag(sl, x, y, t, color=ORANGE, w=3.6):
    b = box(sl, x, y, w, 0.36, None, color, MSO_SHAPE.ROUNDED_RECTANGLE)
    text(sl, x, y + 0.02, w, 0.32, t, 10.5, color, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)

def notes(sl, t): sl.notes_slide.notes_text_frame.text = t

# ---------- P1
sl = prs.slides.add_slide(prs.slide_layouts[6])
box(sl, 0, 0, W, 9.375, BLUE)
sl.shapes.add_picture(str(LOGO), Inches(14.2), Inches(0.6), Inches(1.7), Inches(1.7))
text(sl, 1.1, 1.3, 12, 0.5, 'Software Requirements Engineering · M5 Final', 18, RGBColor(0xAC,0xC7,0xE5))
text(sl, 1.1, 2.55, 14, 1.1, '面向长期对话的动态记忆系统', 46, RGBColor(255,255,255), True)
text(sl, 1.1, 3.75, 14, 0.7, '设计、实现与评测', 28, RGBColor(255,255,255))
box(sl, 1.15, 4.85, 13.8, 0.02, RGBColor(0x5E,0x86,0xB8))
text(sl, 1.1, 5.2, 14, 0.5, '第三组「在阴雨天游泳」', 22, RGBColor(255,255,255), True)
members = [('莫远序', '组长 · 核心系统与实验'), ('黎志丽', 'Product Console'), ('卓新烨', '时间 / 事件 Sidecar'), ('田亦洁', '汇报材料与演示视频')]
for i, (nm, role) in enumerate(members):
    x = 1.1 + i * 3.55
    text(sl, x, 6.0, 3.3, 0.5, nm, 20, RGBColor(255,255,255), True)
    text(sl, x, 6.5, 3.3, 0.4, role, 13.5, RGBColor(0xAC,0xC7,0xE5))
text(sl, 1.1, 8.25, 14, 0.4, 'github.com/kenqia/locomo-dynamic-memory · 2026 年 11 月 9 日', 13, RGBColor(0xAC,0xC7,0xE5))
notes(sl, '大家好，我们是第三组"在阴雨天游泳"。我们的项目是一个面向长期对话的动态记忆系统：它把多次会话整理成带来源、带时间的记忆，回答问题时给出可以回查原文的引用。我是组长莫远序，负责核心系统和实验；黎志丽负责 Web Console，卓新烨负责时间与事件的扩展研究，田亦洁负责汇报材料和演示视频。')

# ---------- P2
sl = frame(2, '问题：相关不等于有效')
headline(sl, '长期对话里，难的是判断一句话"现在还算不算数"', '两句话都和问题高度相关，只有结合时间和关系，才能给出正确答案')
box(sl, 1.0, 2.95, 7.2, 3.5, PALE, LINE)
text(sl, 1.3, 3.15, 6.6, 0.5, '对话里发生了什么', 20, BLUE, True)
text(sl, 1.3, 3.85, 6.7, 2.4, [[('5 月 1 日  ', {'color': GREY, 'size': 17}), ('"I live in Paris."', {'size': 20})],
     [('5 月 2 日  ', {'color': GREY, 'size': 17}), ('"I moved from Paris to Rome."', {'size': 20})], ' ',
     [('相似度检索会同时找到这两句话', {'color': GREY, 'size': 16})]], spacing=1.45)
box(sl, 8.5, 2.95, 7.17, 3.5, PALE, LINE)
text(sl, 8.8, 3.15, 6.6, 0.5, '同一个问题，两种时间', 20, BLUE, True)
text(sl, 8.8, 3.9, 6.6, 0.5, '"Alex 现在住在哪？"', 19)
text(sl, 8.8, 4.45, 6.6, 0.5, '→ Rome', 24, BLUE, True)
text(sl, 8.8, 5.15, 6.6, 0.5, '"Alex 5 月 1 日住在哪？"', 19)
text(sl, 8.8, 5.7, 6.6, 0.5, '→ Paris', 24, TEAL, True)
for i, t in enumerate(['计划 ≠ 已完成', '否定也要保留', '矛盾不能擅自消解']):
    b = box(sl, 1.0 + i * 4.95, 6.85, 4.7, 0.62, RGBColor(255,255,255), LINE, MSO_SHAPE.ROUNDED_RECTANGLE)
    text(sl, 1.0 + i * 4.95, 6.9, 4.7, 0.52, t, 17, DARK, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
text(sl, 1.0, 7.75, 14.67, 0.5, [[('我们想回答：', {'bold': True, 'color': BLUE}), ('查询时多一步"有效证据解析"，能否稳定地提高回答质量？代价多大？证据在哪一步丢失？', {})]], 16)
tag(sl, 12.07, 1.0, '合成示例', ORANGE, 1.4)
notes(sl, '先看一个例子。Alex 5 月 1 日说住在巴黎，第二天说搬到了罗马。问"他住在哪"，这两句话和问题的语义相似度都很高，普通的相似度检索会把它们一起找出来。只有知道哪句话是什么时候说的、后一句替代了前一句，系统才能回答"现在是罗马"；而问 5 月 1 日时，答案又应该是巴黎。类似的还有计划和完成、否定、前后矛盾。这引出了我们的三个问题。')

# ---------- P3
sl = frame(3, '需求与系统概览')
headline(sl, '五个阶段的需求，落在同一个可追溯的系统里')
steps = ['导入对话', '构建记忆', '检查记忆', '问答', '评测']
for i, s in enumerate(steps):
    x = 1.0 + i * 2.95
    box(sl, x, 2.25, 2.6, 0.75, BLUE if i in (1, 3) else PALE, LINE, MSO_SHAPE.ROUNDED_RECTANGLE)
    text(sl, x, 2.3, 2.6, 0.65, s, 18, RGBColor(255,255,255) if i in (1, 3) else DARK, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    if i < 4: text(sl, x + 2.6, 2.33, 0.35, 0.6, '›', 24, GREY, True, PP_ALIGN.CENTER)
pic(sl, FIG / 'F1s_architecture_slide.png', 1.0, 3.45, w=14.67)
card(sl, 1.0, 5.75, 7.2, 2.75, '技术选择', ['Streamlit 页面 → FastAPI → SQLite', 'BM25 + 本地向量模型（MiniLM，384 维）', 'DeepSeek deepseek-flash：抽取、关系、回答'], bsize=16)
card(sl, 8.47, 5.75, 7.2, 2.75, '三条质量要求', ['可追溯：任何回答都能定位到原文', '版本一致：一次查询只用一个完整版本', '失败可见：失败被记录，不当成"没有结果"'], bsize=16)
notes(sl, '在 M3 的需求规格里，我们把系统使用过程分成五个阶段：导入、构建、检查、问答和评测。最终系统完整实现了这五个阶段。架构上，页面只通过 FastAPI 访问后端，数据存在 SQLite 里；检索用 BM25 加本地向量模型，抽取和回答调用 DeepSeek。我们最看重三条质量要求：可追溯、版本一致、失败可见。')

# ---------- P4
sl = frame(4, '构建与查询流程')
headline(sl, 'Hybrid 与 Dynamic 共享检索和历史扩展，只差"解析"这一步', 'Dynamic 多调用一次模型，从候选中挑出对这个问题、这个时间有效的记忆')
pic(sl, FIG / 'F3_pipelines.png', 1.0, 2.75, w=14.67)
box(sl, 1.0, 7.35, 14.67, 1.1, PALE, LINE)
text(sl, 1.3, 7.48, 14.2, 0.9, [[('构建：', {'bold': True, 'color': BLUE}), ('按片段保存进度，失败只重试失败片段；任何一步没完成，版本就不发布，旧版本继续可用。', {})],
     [('查询：', {'bold': True, 'color': BLUE}), ('BM25 与向量各取 20 → RRF 融合 → 历史扩展（≤ 60 条）→ [解析] → 回答，并记录四阶段 Trace。', {})]], 15.5, spacing=1.35)
notes(sl, '这是构建和查询的流程。构建按片段进行，任何一步失败都不会覆盖旧版本。查询时，两种策略都先做混合检索，再沿已有关系扩展相关历史。Hybrid 直接把候选交给回答模型；Dynamic 先多调用一次模型，从最多 60 条候选里选出真正有效的记忆，再回答。两种策略唯一的区别就是这一步，后面的实验比较的就是它值不值得。')

# ---------- P5
sl = frame(5, '记忆模型与时间语义')
headline(sl, '新信息不覆盖旧信息，每个回答都能回到原文')
pic(sl, FIG / 'F2s_memory_slide.png', 1.0, 2.25, w=14.67)
card(sl, 1.0, 6.4, 4.7, 2.1, '原子记忆', ['一条记忆 = 一个事实', '指向原始轮次，记录计划 / 否定'], bsize=15.5)
card(sl, 5.98, 6.4, 4.7, 2.1, '记忆关系', ['替代 · 推进 · 冲突 · 保留 · 未确定', '当前状态可随时重算'], bsize=15.5)
card(sl, 10.97, 6.4, 4.7, 2.1, '两种时间', ['报告时间 ≠ 事件时间', '"现在" = 最后一次会话'], bsize=15.5)
tag(sl, 13.47, 1.0, '合成示例', ORANGE, 1.4)
notes(sl, '这是我们的数据模型。一条记忆只表达一个事实，并指向原始轮次。巴黎和罗马之间是替代关系：当前状态更新为罗马，但巴黎这条历史仍保留，用来回答历史问题。Sam 的两个出生年份是冲突关系，系统保留双方来源而不是挑一个。时间上，我们分开记录"话是什么时候说的"和"事情是什么时候发生的"。')

# ---------- P6
sl = frame(6, '真实运行的 Web Console')
headline(sl, '在 Console 里，可以从回答一路检查到原文和每个阶段的证据')
pic(sl, SHOT / '04-query-current.png', 1.0, 2.2, w=7.2, border=True)
pic(sl, SHOT / '06-trace-effective-delivered.png', 8.47, 2.2, w=7.2, border=True)
text(sl, 1.0, 6.35, 7.2, 0.4, '当前事实："Alex lives in Rome."，引用 D2:1 原文', 14, GREY)
text(sl, 8.47, 6.35, 7.2, 0.4, '历史日期问题：切换到"有效证据"阶段的 Trace', 14, GREY)
box(sl, 1.0, 7.0, 14.67, 1.45, PALE, LINE)
text(sl, 1.3, 7.12, 14.1, 1.25, [[('五个页面：', {'bold': True, 'color': BLUE}), ('Overview · Memory · Query · Experiments · Demo；只读浏览，不会自动构建或调用模型', {})],
     [('工程质量：', {'bold': True, 'color': BLUE}), ('主分支持续集成通过；离线测试 1,018 项全部通过；组员真人复核', {})]], 15.5, spacing=1.45)
tag(sl, 12.07, 1.0, 'OFFLINE SYNTHETIC REPLAY', ORANGE, 3.6)
notes(sl, '这是合并进主分支的 Web Console 的真实页面，截图来自离线演示模式，使用合成数据，不调用模型。左边是"Alex 现在住在哪"的回答和它引用的原文；右边是历史日期问题的 Trace，可以逐阶段切换，看初始候选、扩展、有效证据和最终引用。这个界面由黎志丽开发，卓新烨做了非作者复核；主分支的 1,018 项离线测试全部通过。')

# ---------- P7
sl = frame(7, '实验设计')
headline(sl, '最终结论来自一次事先固定配置的独立留出实验')
for i, (n, t, b) in enumerate([('400', '题目', 'conv-43 / conv-44\n开发期间从未看过成绩'), ('2', '策略', 'Hybrid 与 Dynamic\n每道题各运行一次'), ('0', '分', '失败题记 0 分\n不补跑、不删除')]):
    x = 1.0 + i * 4.95
    box(sl, x, 2.3, 4.7, 2.4, PALE, LINE)
    text(sl, x + 0.3, 2.45, 4.2, 1.0, [[(n, {'size': 46, 'bold': True, 'color': BLUE}), ('  ' + t, {'size': 20, 'color': GREY})]])
    text(sl, x + 0.3, 3.55, 4.2, 1.0, b.split('\n'), 16, DARK, spacing=1.3)
text(sl, 1.0, 5.05, 14.67, 0.5, '三条原则', 20, BLUE, True)
for i, t in enumerate(['先固定配置，再看答案', '每道题只跑一次', '确认结果完整后才评分']):
    x = 1.0 + i * 4.95
    box(sl, x, 5.6, 4.7, 0.75, RGBColor(255,255,255), LINE, MSO_SHAPE.ROUNDED_RECTANGLE)
    text(sl, x, 5.65, 4.7, 0.65, f'{i+1}  {t}', 17, DARK, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
text(sl, 1.0, 6.75, 14.67, 1.6, [[('指标：', {'bold': True, 'color': BLUE}), ('事实类问题用官方 token F1；逐题配对 bootstrap 求 95% 区间；同时记录费用、延迟和失败。', {})],
     [('开发阶段：', {'bold': True, 'color': BLUE}), ('757 题和 100 题的多轮实验用来发现问题、确定配置；样本与配置不同，不和最终结果比较。', {})]], 16, spacing=1.5)
notes(sl, '开发阶段我们在四段开发对话上做了多轮实验，它们帮助我们发现问题、确定配置，但样本和配置都不同，不能和最终结果放在一起比较。最终结论只来自这次实验：两段开发期间从未看过成绩的对话，共 400 道题，两种策略各跑一次。配置在看答案之前固定，失败的题记 0 分不补跑，结果确认完整后才评分。')

# ---------- P8
sl = frame(8, '核心实验结果')
headline(sl, 'Dynamic 的 F1 点估计略高但区间跨零；费用和延迟高出数倍')
pic(sl, FIG / 'S5_f1.png', 1.0, 2.2, w=8.3)
pic(sl, FIG / 'S6_cost_latency.png', 1.0, 5.35, w=8.3)
for i, (big, lab, sub, col) in enumerate([('0.403 vs 0.409', '事实类 token F1', '差 +0.007，95% 区间 [−0.020, +0.034]', DARK),
                                           ('7.90×', '估算查询费用', '按已报 token 用量估算，不是实际账单', ORANGE),
                                           ('3.51×', '单题中位延迟', '2.37 秒 vs 8.31 秒', ORANGE)]):
    y = 2.2 + i * 1.95
    box(sl, 9.6, y, 6.07, 1.75, PALE, LINE)
    text(sl, 9.9, y + 0.12, 5.6, 0.75, big, 32, col, True)
    text(sl, 9.9, y + 0.88, 5.6, 0.4, lab, 16, BLUE, True)
    text(sl, 9.9, y + 1.25, 5.6, 0.4, sub, 13, GREY)
text(sl, 9.6, 8.12, 6.07, 0.55, '成功 394 vs 389 / 400；17 次失败中 9 次为供应商余额不足', 12.5, GREY)
notes(sl, '这是核心结果。事实类问题上，Hybrid 的 F1 是 0.403，Dynamic 是 0.409，差值的 95% 区间从负 0.020 到正 0.034，跨过零。所以在这次实验的设定下，我们没有足够证据说明 Dynamic 有稳定的质量优势——这并不等于说它没用。另一方面，Dynamic 按已报用量估算的费用约是 Hybrid 的 7.9 倍，几乎全部来自解析这一步；中位延迟约 3.5 倍。成功率略低，但 17 次失败里有 9 次是账户余额不足，不能都算在方法上。')

# ---------- P9
sl = frame(9, '证据保留与未采用的扩展')
headline(sl, '标注来源主要在解析步骤减少；扩展方向没有显示问答收益')
pic(sl, FIG / 'S7_evidence.png', 1.0, 2.15, w=8.6)
box(sl, 1.0, 5.85, 8.6, 2.65, PALE, LINE)
text(sl, 1.3, 5.95, 8.1, 2.6, [[('107', {'size': 30, 'bold': True, 'color': ORANGE}), (' / 400 题在解析后少了至少一个标注来源', {'size': 16})],
     [('2', {'size': 30, 'bold': True, 'color': BLUE}), (' / 400 题在回答阶段因篇幅限制再丢失', {'size': 16})],
     [('这不是 107 次错误删除：标注来源不一定是必需证据，例如问 Tim、来源却在讲 John。哪些排除是错的，还需要人工逐题判断。', {'size': 14, 'color': GREY})]], spacing=1.25)
text(sl, 10.0, 2.2, 5.67, 0.5, '尝试过但没有采用', 20, BLUE, True)
rows = [('Graph 两跳检索', '最终证据覆盖不变'), ('记忆压缩', '节省可以忽略'), ('自适应路由', '证据覆盖下降'), ('时间软优先', '没有整体收益'), ('时间 / 事件 Sidecar', '研究候选，未进主分支')]
for i, (a, b) in enumerate(rows):
    y = 2.85 + i * 1.12
    box(sl, 10.0, y, 5.67, 0.95, RGBColor(255,255,255), LINE)
    text(sl, 10.25, y + 0.08, 5.3, 0.4, a, 16, DARK, True)
    text(sl, 10.25, y + 0.5, 5.3, 0.4, b, 13.5, GREY)
notes(sl, '为什么 Dynamic 没有带来收益？我们按阶段统计了标注来源的覆盖。Hybrid 从头到尾基本不变；Dynamic 在解析这一步从 0.68 降到 0.53。逐题看，107 道题在解析后少了至少一个标注来源，只有 2 道题是在回答阶段丢的。但要注意，这不是 107 次错误删除——标注来源不一定是回答必需的，比如有道题问 Tim，来源却在讲 John，排除它可能是对的。右边是我们尝试过的几个扩展，都没有显示出问答收益，所以默认关闭。卓新烨的时间 Sidecar 作为独立研究候选保留。')

# ---------- P10
sl = frame(10, '结论与未来工作')
headline(sl, '默认 Hybrid，Dynamic 显式可选')
card(sl, 1.0, 2.2, 7.2, 4.6, '我们的结论', ['系统：从原文到记忆、关系、版本和带引用回答的完整链路，可以在网页中逐层检查',
     '质量：区间跨零，没有证明 Dynamic 稳定更好', '代价：估算费用约 7.9 倍，中位延迟约 3.5 倍', '证据：减少集中在解析步骤，原因仍待判断'], bsize=16.5)
card(sl, 8.47, 2.2, 7.2, 4.6, '下一步', ['人工核查 20 个证据保留案例，区分合理与错误的排除', '建立人工核查的动态关系标签，测量关系准确率',
     '改进解析步骤后，在新的未公开对话上重新评测', '扩大评测对话数量'], tcolor=TEAL, bsize=16.5)
box(sl, 1.0, 7.1, 14.67, 1.3, BLUE)
text(sl, 1.3, 7.2, 14.1, 1.1, ['一个看起来合理的设计，在独立数据上没有显示稳定收益，同时付出了明显成本。', '我们把它如实记录下来，并据此做出工程选择。'], 18, RGBColor(255,255,255), True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, 1.35)
notes(sl, '总结一下。工程上，我们交付了从原文到记忆、关系、版本和带引用回答的完整系统，每一步都可以在网页里检查。研究上，我们设计的动态解析在独立数据上没有显示出稳定优势，同时更贵、更慢，而且是证据减少的主要位置。所以我们默认使用 Hybrid，Dynamic 作为可选项保留。下一步最值得做的，是人工核查那些被排除的证据到底该不该排除，再在新的数据上重新评测。谢谢大家。')

prs.save(str(OUT)); print('saved', OUT, len(prs.slides))
