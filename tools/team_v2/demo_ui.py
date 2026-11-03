"""Show the ordinary application with an explicit synthetic-demo banner."""
from pathlib import Path
import runpy
import streamlit as st

st.set_page_config(page_title='LoCoMo offline synthetic demo', layout='wide')
st.warning('OFFLINE SYNTHETIC DEMO · 合成案例与受控模型适配器 · 0 次真实模型请求 · 不代表真实 QA 质量')
runpy.run_path(str(Path(__file__).resolve().parents[2] / 'src/locomo_memory/ui.py'), run_name='__main__')
