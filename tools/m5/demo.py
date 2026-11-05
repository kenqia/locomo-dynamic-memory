"""Read-only Streamlit demonstration of frozen real development data."""
import streamlit as st

from locomo_memory.m5_ui import render_bonus
from tools.m5.demo_backend import resources
from tools.m5.offline import DEV

resources = st.cache_resource(resources)

st.set_page_config(page_title='M5 · 真实开发数据只读演示', layout='wide')
st.title('M5 · 真实开发数据只读演示')
st.caption('冻结开发 Build；仅图浏览、状态关系与原文。无模型调用。历史关系可能有语义错误，图连通不代表事实正确。')
bundles, client = resources()
conversation = st.selectbox('开发对话', list(DEV))
bundle = bundles[conversation]
st.caption(f'Build {bundle.build.build_id} · {len(bundle.memories)} Memory · {len(bundle.relations)} relations')


def request(method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


render_bonus(request, bundle.build.model_dump(mode='json'))
