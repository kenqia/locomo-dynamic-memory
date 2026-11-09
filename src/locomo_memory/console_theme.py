"""Responsive presentation scoped to the Product Console, including its popovers."""
import streamlit as st


CONSOLE_CSS = """
<style>
[data-testid="stAppViewContainer"]:has(.st-key-console_header) { background: #f3f7fc; }
[data-testid="stMainBlockContainer"]:has(.st-key-console_header) {
  --dm-bg: #f3f7fc; --dm-panel: #fff; --dm-panel-soft: #eef5ff;
  --dm-ink: #111827; --dm-muted: #536176; --dm-line: #d7e2ef;
  --dm-line-strong: #b8cbe0; --dm-accent: #2563a6;
  --dm-accent-dark: #174b82; --dm-accent-soft: #e5f0ff;
  max-width: 1840px; width: 100%; padding: 1.25rem clamp(1rem, 3vw, 3rem) 3rem !important;
  container-type: inline-size; container-name: product-page;
}
body:has(.st-key-console_header) [data-testid="stMarkdownContainer"] p,
body:has(.st-key-console_header) [data-testid="stText"] {
  font-size: 1.08rem; line-height: 1.7; overflow-wrap: anywhere;
}
body:has(.st-key-console_header) [data-testid="stCaptionContainer"] {
  color: #536176; opacity: 1;
}
body:has(.st-key-console_header) [data-testid="stCaptionContainer"] p {
  color: #536176; font-size: .96rem; line-height: 1.65;
}
body:has(.st-key-console_header) h2 { font-size: clamp(1.5rem, 2.2vw, 2rem) !important; }
body:has(.st-key-console_header) h3 { font-size: clamp(1.2rem, 1.7vw, 1.5rem) !important; }
body:has(.st-key-console_header) [data-testid="stChatMessage"] { max-width: none; }
body:has(.st-key-console_header) [data-testid="stJson"] { max-width: 100%; max-height: 32rem; overflow: auto; }
body:has(.st-key-console_header) [data-testid="stTable"] { width: 100%; }
body:has(.st-key-console_header) [data-testid="stTable"] table { width: 100%; table-layout: fixed; }
body:has(.st-key-console_header) [data-testid="stTable"] td,
body:has(.st-key-console_header) [data-testid="stTable"] th {
  font-size: 1rem; padding: .8rem; overflow-wrap: anywhere; white-space: normal;
}
body:has(.st-key-console_header) [data-testid="stMetricValue"] {
  font-size: clamp(1.65rem, 2.7vw, 2.5rem); white-space: normal; overflow: visible;
}
body:has(.st-key-console_header) [data-testid="stMetricValue"] [data-testid="stMarkdownContainer"] p {
  font-size: inherit; line-height: 1.3;
}
body:has(.st-key-console_header) [data-testid="stMetricLabel"] p { font-size: .96rem; }
body:has(.st-key-console_header) [data-testid="stMetric"] { min-width: 0; padding: 1rem; }
body:has(.st-key-console_header) [data-testid="stSelectbox"] { max-width: 32rem; }
body:has(.st-key-console_header) [data-testid="stSelectbox"] label p { white-space: normal; }
body:has(.st-key-console_header) button { border-color: #bfd0e4; }
body:has(.st-key-console_header) .stButton > button p { white-space: normal; }
body:has(.st-key-console_header) button:hover { background: #eaf3ff; border-color: #8eafd5; }
body:has(.st-key-console_header) button[kind="primary"] { background: #111827; border-color: #111827; color: white; }
body:has(.st-key-console_header) button:focus-visible,
body:has(.st-key-console_header) input:focus { outline-color: #2563a6; border-color: #2563a6 !important; }
body:has(.st-key-console_header) [data-testid="stRadioOption"] {
  border: 1px solid #d7e2ef; background: #fff; padding: .5rem .85rem; border-radius: .55rem;
}
body:has(.st-key-console_header) [data-testid="stRadio"] > label { border: 0; background: transparent; padding: 0; }
body:has(.st-key-console_header) [data-testid="stRadioOption"][data-selected="true"] {
  color: #111827; border-color: #90b5df; background: #e5f0ff;
}
body:has(.st-key-console_header) [data-testid="stRadioOption"]:has(input:focus-visible) {
  outline: 2px solid #2563a6; outline-offset: 3px;
}
body:has(.st-key-console_header) [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {
  display: none;
}
.st-key-console_header { container-type: inline-size; container-name: product-header; margin-bottom: 1rem;
  background: white; border-bottom: 1px solid #cddced; padding: .5rem 0; }
.st-key-console_header [data-testid="stHorizontalBlock"] { align-items: center; flex-wrap: wrap; gap: 1rem; }
.st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: 0; }
.st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) { flex: 0 0 240px; min-height: 68px; }
.st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) { flex: 1 1 520px; }
.st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) { flex: 0 0 120px; }
.console-brand { display: flex; align-items: center; gap: .8rem; min-height: 3.5rem; }
.console-brand-mark { width: 44px; height: 44px; flex: 0 0 44px; display: grid; place-items: center;
  border-radius: 10px; background: #111827; color: white; font-size: 1rem; font-weight: 750; }
.console-brand-title { color: #111827; font-size: 1.45rem; font-weight: 730; white-space: nowrap; }
.st-key-console_nav [data-testid="stRadio"] > label { display: none; }
.st-key-console_nav [role="radiogroup"] { display: flex; flex-wrap: wrap; gap: .4rem; }
.st-key-console_nav [data-testid="stRadioOption"] {
  border: 0 !important; border-bottom: 3px solid transparent !important; background: transparent !important;
  border-radius: 0 !important; padding: .9rem .85rem !important; margin: 0 !important;
}
.st-key-console_nav [data-testid="stRadioOption"] p { font-size: 1.1rem !important; font-weight: 560; white-space: nowrap; }
.st-key-console_nav [data-testid="stRadioOption"][data-selected="true"] {
  border-bottom-color: #2563a6 !important; color: #174b82; background: #f0f6ff !important;
}
.console-context { display: flex; flex-wrap: wrap; align-items: center; gap: .65rem; font-size: 1rem; }
.console-context span { display: inline-block; padding: .3rem .7rem; border-radius: 6px;
  background: #e5f0ff; color: #263e58; }
@container product-header (max-width: 1040px) {
  .st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) { flex: 1 1 calc(100% - 140px); order: 0; }
  .st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) { flex: 1 1 100%; order: 2; }
  .st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) { order: 1; }
}
@container product-page (max-width: 900px) {
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: 0; }
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"] { flex: 1 1 calc(50% - 1rem); }
  .st-key-console_memory_layout [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { flex: 1 1 100%; }
}
@container product-header (max-width: 600px) {
  .console-brand-title { font-size: 1.22rem; }
  .console-brand-mark { width: 38px; height: 38px; flex-basis: 38px; }
  .st-key-console_header [data-testid="stHorizontalBlock"] { gap: .4rem; }
  .st-key-console_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) { flex-basis: 120px; }
  .st-key-console_nav [role="radiogroup"] { gap: .12rem; justify-content: space-between; }
  .st-key-console_nav [data-testid="stRadioOption"] { padding: .65rem .35rem !important; }
  .st-key-console_nav [data-testid="stRadioOption"] p { font-size: .9rem !important; }
}
@container product-page (max-width: 600px) {
  [data-testid="stHorizontalBlock"]:not(.st-key-console_header *) > [data-testid="stColumn"] { flex: 1 1 100%; }
  [data-testid="stHorizontalBlock"]:not(.st-key-console_header *):has(> [data-testid="stColumn"]:nth-child(4)) > [data-testid="stColumn"] { flex: 1 1 calc(50% - 1rem); }
}
</style>
"""


def apply_console_theme():
    st.markdown(CONSOLE_CSS, unsafe_allow_html=True)
