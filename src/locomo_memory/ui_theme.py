"""Shared visual language for the Streamlit workflow."""

from html import escape

import streamlit as st


WORKFLOW_STEPS = (
    (1, "上传数据"),
    (2, "选择对话"),
    (3, "构建记忆"),
    (4, "证据问答"),
    (5, "评测报告"),
)


APP_CSS = """
<style>
:root {
  --dm-bg: #f7f7f8;
  --dm-panel: #ffffff;
  --dm-panel-soft: #fbfbfc;
  --dm-ink: #171717;
  --dm-muted: #6b6b70;
  --dm-line: #e4e4e7;
  --dm-line-strong: #d4d4d8;
  --dm-accent: #10a37f;
  --dm-accent-dark: #08745b;
  --dm-accent-soft: #e9f7f2;
  --dm-warning: #b45309;
}

html { scroll-behavior: smooth; }
body, [class*="css"] {
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--dm-ink);
}
[data-testid="stAppViewContainer"] { background: var(--dm-bg); }
[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1260px;
  padding: .45rem 1.4rem 2rem;
}
[data-testid="stMainBlockContainer"] {
  max-width: 1260px;
  padding-top: .35rem !important;
  padding-bottom: 2rem !important;
}
[data-testid="stMainBlockContainer"]:has(.dm-page-upload-marker),
.block-container:has(.dm-page-upload-marker) { max-width: 1320px; }
.dm-page-upload-marker { display: none; }
.dm-page-conversation-marker, .dm-upload-panel-marker, .dm-conversation-card-marker { display: none; }
[data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stVerticalBlock"] { gap: .72rem; }
[data-testid="stHorizontalBlock"] { gap: .72rem; }

.dm-shell-head {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  margin: 0 0 .48rem;
}
.dm-brand { display: flex; gap: .72rem; align-items: center; }
.dm-brand-mark {
  width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: #171717; color: white; font-size: 13px; font-weight: 760;
}
.dm-brand-title { font-size: .96rem; font-weight: 720; line-height: 1.2; }
.dm-brand-subtitle { color: var(--dm-muted); font-size: .72rem; margin-top: .18rem; }
.dm-step-count {
  border: 1px solid var(--dm-line); border-radius: 999px; background: white;
  color: var(--dm-muted); font-size: .74rem; font-weight: 650; padding: .38rem .72rem;
}

.dm-stepper {
  display: grid; grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: .35rem; padding: .35rem; border: 1px solid var(--dm-line);
  border-radius: 13px; background: white; margin-bottom: .72rem;
}
.dm-step {
  display: flex; align-items: center; gap: .52rem; min-width: 0;
  border-radius: 9px; padding: .42rem .58rem; color: #8a8a8f;
  font-size: .78rem; font-weight: 630;
}
.dm-step-index {
  width: 1.45rem; height: 1.45rem; flex: 0 0 1.45rem; border-radius: 50%;
  display: grid; place-items: center; border: 1px solid #d9d9dd;
  font-size: .68rem; font-variant-numeric: tabular-nums;
}
.dm-step.done { color: var(--dm-accent-dark); background: #f5fbf9; }
.dm-step.done .dm-step-index { background: var(--dm-accent-soft); border-color: #b8e2d7; }
.dm-step.active { color: white; background: #171717; }
.dm-step.active .dm-step-index { border-color: rgba(255,255,255,.55); }
.dm-step-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.dm-hero {
  padding: .82rem 1.05rem .78rem; border: 1px solid var(--dm-line);
  border-radius: 15px; background: white; margin-bottom: .72rem;
}
.dm-eyebrow {
  color: var(--dm-accent-dark); font-size: .7rem; font-weight: 720;
  letter-spacing: .09em; text-transform: uppercase; margin: 0 0 .25rem !important;
}
.dm-hero h1 { margin: 0 !important; font-size: clamp(1.55rem, 3vw, 2rem); letter-spacing: -.04em; line-height: 1.1; }
.dm-hero p { margin: .3rem 0 0 !important; max-width: 1000px; color: var(--dm-muted); font-size: .88rem; line-height: 1.55; }

.dm-context {
  display: flex; flex-wrap: wrap; gap: .4rem; margin: -.12rem 0 .6rem;
}
.dm-context-item {
  border: 1px solid var(--dm-line); border-radius: 999px; background: white;
  color: var(--dm-muted); font-size: .72rem; padding: .34rem .68rem;
}
.dm-context-item strong { color: #303036; font-weight: 680; }
.dm-section-kicker {
  color: var(--dm-accent-dark); font-size: .7rem; font-weight: 720;
  letter-spacing: .08em; text-transform: uppercase; margin: 1rem 0 -.15rem;
}
.dm-card-title { font-size: .96rem; font-weight: 720; margin-bottom: .18rem; }
.dm-card-copy {
  color: var(--dm-muted); font-size: .82rem; line-height: 1.55;
  margin-bottom: .55rem; text-wrap: pretty;
}
.dm-inline-title {
  display: flex; align-items: baseline; gap: .65rem; flex-wrap: wrap;
  color: var(--dm-muted); font-size: .82rem; line-height: 1.5;
}
.dm-inline-title strong { color: var(--dm-ink); font-size: .96rem; font-weight: 720; white-space: nowrap; }
.dm-status {
  display: inline-flex; align-items: center; gap: .36rem; padding: .3rem .62rem;
  border-radius: 999px; background: var(--dm-accent-soft); color: var(--dm-accent-dark);
  font-size: .72rem; font-weight: 680;
}
.dm-status::before { content: ""; width: .42rem; height: .42rem; border-radius: 50%; background: var(--dm-accent); }
.dm-build-ready {
  border-radius: 10px; background: var(--dm-accent-soft); color: var(--dm-accent-dark);
  font-size: .82rem; line-height: 1.45; padding: .52rem .75rem;
}
.dm-muted-note { color: var(--dm-muted); font-size: .78rem; line-height: 1.6; }
.dm-answer-meta {
  display: inline-flex; align-items: center; gap: .4rem; padding: .3rem .62rem;
  border-radius: 999px; background: var(--dm-accent-soft); color: var(--dm-accent-dark);
  font-size: .73rem; font-weight: 650;
}

h1, h2, h3 { color: var(--dm-ink); letter-spacing: -.025em; }
h2 { margin-top: .25rem !important; font-size: 1.32rem !important; }
h3 { margin-top: .8rem !important; font-size: 1.02rem !important; }
h4, h5 { margin-top: .45rem !important; margin-bottom: .1rem !important; }
p, [data-testid="stCaptionContainer"] { line-height: 1.62; }
[data-testid="stCaptionContainer"] { color: var(--dm-muted); }
[data-testid="stCaptionContainer"] p, .dm-hero p { text-wrap: pretty; }
hr { border-color: var(--dm-line); }

div[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-color: var(--dm-line) !important; border-radius: 13px !important;
  background: var(--dm-panel); padding: .82rem .9rem;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.dm-upload-panel-marker),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.dm-upload-panel-marker) > div {
  height: 100%; min-height: 390px;
}
[data-testid="stMainBlockContainer"]:has(.dm-page-upload-marker) .dm-hero {
  padding-top: 1.05rem; padding-bottom: 1rem;
}
[data-testid="stMainBlockContainer"]:has(.dm-page-upload-marker)
div[data-testid="stVerticalBlockBorderWrapper"]:has(.dm-upload-panel-marker) {
  min-height: 390px;
}
[data-testid="stMainBlockContainer"]:has(.dm-page-upload-marker)
[data-testid="stColumn"] [data-testid="stVerticalBlock"]:has(.dm-upload-panel-marker) {
  min-height: 390px; justify-content: space-between;
}
[data-testid="stHorizontalBlock"]:has(.dm-upload-panel-marker) > [data-testid="stColumn"] {
  display: flex; flex-direction: column;
}
[data-testid="stHorizontalBlock"]:has(.dm-upload-panel-marker) > [data-testid="stColumn"] > div {
  flex: 1;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.dm-conversation-card-marker) > div {
  min-height: 96px; padding: 1rem 1.1rem;
}
[data-testid="stMainBlockContainer"]:has(.dm-page-conversation-marker) [data-testid="stMetric"] {
  min-height: 112px; padding: .9rem 1rem;
}
div[data-testid="stExpander"] {
  border: 1px solid var(--dm-line); border-radius: 12px; background: white;
  box-shadow: none; overflow: hidden;
}
div[data-testid="stExpander"] details summary { padding: .08rem .15rem; }
div[data-testid="stDataFrame"] { border: 1px solid var(--dm-line); border-radius: 12px; overflow: hidden; }
[data-testid="stJson"] { border-radius: 12px; }
[data-testid="stMetric"] {
  background: var(--dm-panel); border: 1px solid var(--dm-line); border-radius: 12px; padding: .62rem .78rem;
}

.stButton > button, .stDownloadButton > button {
  min-height: 2.25rem; border-radius: 10px; border: 1px solid var(--dm-line-strong);
  background: white; color: #171717; font-weight: 640; padding: .36rem .78rem;
  box-shadow: none; transition: background .15s ease, border-color .15s ease, transform .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background: #f4f4f5; border-color: #b9b9be; color: #111; transform: translateY(-1px);
}
.stButton > button p, .stDownloadButton > button p { white-space: nowrap; }
.stButton > button[kind="primary"] { background: #171717; color: white; border-color: #171717; }
.stButton > button[kind="primary"]:hover { background: #303030; color: white; }

[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input, [data-testid="stTextArea"] textarea {
  border-color: #dcdcdf !important; border-radius: 12px !important; background: white !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  min-height: 2.55rem; border-color: #dcdcdf; border-radius: 12px; background: white;
}
[data-testid="stSelectbox"] label p, [data-testid="stTextInput"] label p { white-space: nowrap; }
[data-testid="stTextArea"] textarea { min-height: 120px; padding: .85rem 1rem; }
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
  border-color: #a8a8ad !important; box-shadow: 0 0 0 1px #a8a8ad !important;
}
[data-testid="stFileUploaderDropzone"] {
  border: 1px dashed #c8c8cd; border-radius: 12px; background: var(--dm-panel-soft);
  padding: .72rem;
}
[data-testid="stAlert"] { border-radius: 13px; }
[data-testid="stProgressBar"] > div > div { background-color: var(--dm-accent); }

[data-testid="stRadio"] > div { gap: .5rem; }
[data-testid="stRadio"] label {
  border: 1px solid var(--dm-line); border-radius: 12px; background: white;
  padding: .48rem .7rem; margin: 0;
}
[data-testid="stChatMessage"] {
  background: white; border: 1px solid var(--dm-line); border-radius: 16px;
  padding: 1rem 1.1rem; max-width: 1100px;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"] { background: #ececee; }
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] { background: #171717; }

@media (max-width: 760px) {
  [data-testid="stAppViewContainer"] > .main .block-container { padding: .45rem .75rem 2rem; }
  .dm-stepper { grid-template-columns: 1fr; gap: .2rem; }
  .dm-step:not(.active) { display: none; }
  .dm-hero { padding: 1.2rem; }
  .dm-hero h1 { font-size: 1.8rem; }
  .dm-shell-head { align-items: flex-start; }
}
</style>
"""


def apply_app_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_workflow_header(current_step: int) -> None:
    step_items = []
    for index, label in WORKFLOW_STEPS:
        state = "active" if index == current_step else "done" if index < current_step else ""
        marker = "✓" if index < current_step else f"{index:02d}"
        step_items.append(
            f'<div class="dm-step {state}"><span class="dm-step-index">{marker}</span>'
            f'<span class="dm-step-label">{escape(label)}</span></div>'
        )
    st.markdown(
        f"""
        <div class="dm-shell-head">
          <div class="dm-brand">
            <div class="dm-brand-mark">DM</div>
            <div><div class="dm-brand-title">Dynamic Memory</div>
            <div class="dm-brand-subtitle">长期对话证据工作流</div></div>
          </div>
          <div class="dm-step-count">第 {current_step} / {len(WORKFLOW_STEPS)} 步</div>
        </div>
        <div class="dm-stepper">{''.join(step_items)}</div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <header class="dm-hero">
          <div class="dm-eyebrow">{escape(eyebrow)}</div>
          <h1>{escape(title)}</h1>
          <p>{escape(description)}</p>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_context(dataset_id: str | None = None, sample_id: str | None = None, build_id: str | None = None) -> None:
    entries = []
    for label, value in (("数据集", dataset_id), ("对话", sample_id), ("构建", build_id)):
        if value:
            entries.append(f'<span class="dm-context-item"><strong>{label}</strong> {escape(value)}</span>')
    if entries:
        st.markdown(f'<div class="dm-context">{"".join(entries)}</div>', unsafe_allow_html=True)


def section_anchor(name: str, kicker: str | None = None) -> None:
    st.markdown(f'<span id="{escape(name)}"></span>', unsafe_allow_html=True)
    if kicker:
        st.markdown(f'<div class="dm-section-kicker">{escape(kicker)}</div>', unsafe_allow_html=True)
