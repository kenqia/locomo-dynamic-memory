"""No API, database or model: replay only the public, hash-checked bundle."""
from pathlib import Path

import streamlit as st

from locomo_memory.console_replay import ReplayStore
from locomo_memory.console_ui import render_console
from locomo_memory.ui_theme import apply_app_theme

ROOT = Path(__file__).resolve().parents[2]
st.set_page_config(page_title='LoCoMo offline Replay', layout='wide')
apply_app_theme()
try:
    store = ReplayStore(ROOT / 'demo_fixture/product-v1')
except (OSError, ValueError, KeyError):
    st.error('Replay 快照缺失、格式不兼容或校验失败，请恢复完整的 demo_fixture/product-v1。')
    st.stop()
render_console(store.request, evidence_path=store.evidence_path, replay_cases=store.cases)
