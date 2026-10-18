"""Chinese source browser. Every data operation goes through the HTTP API."""

import json

import httpx
import streamlit as st

from locomo_memory.config import load_settings


settings = load_settings()
st.set_page_config(page_title="动态对话记忆", layout="wide")
st.title("动态对话记忆 · 原始来源")
st.caption("导入原始英文对话并核对来源。记忆构建与问答将在后续票中实现。")


def request(method: str, path: str, **kwargs):
    try:
        response = httpx.request(method, f"{settings.api_url.rstrip('/')}{path}", timeout=60, **kwargs)
        if response.is_error:
            try:
                error = response.json()["error"]
                st.error(f"{error['code']}：{error['message']}")
            except (ValueError, KeyError, TypeError):
                st.error("后端返回了无法识别的错误。")
            st.stop()
        return response.json()
    except httpx.HTTPError:
        st.error("无法连接后端，请检查 FastAPI 是否已启动。")
        st.stop()


with st.expander("导入 LoCoMo 数据", expanded=True):
    if st.button("导入仓库官方数据（校验版本与许可证）"):
        result = request("POST", "/imports/official")
        st.success(f"{'已存在' if result['reused'] else '已导入'}：{result['conversation_count']} 段对话，{result['turn_count']} 轮")
        st.json(result)
    uploaded = st.file_uploader("选择本地 LoCoMo JSON", type=["json"])
    version = st.text_input("数据版本", value="local-v1")
    license_name = st.text_input("许可证", value="CC-BY-NC-4.0")
    if st.button("导入选择的文件", disabled=uploaded is None):
        try:
            data = json.loads(uploaded.getvalue())
        except (ValueError, UnicodeError):
            st.error("文件必须为有效的 UTF-8 JSON。")
        else:
            result = request("POST", "/imports/file", files={"file": (uploaded.name, uploaded.getvalue(), "application/json")}, data={"version": version, "license": license_name})
            st.success(f"{'已存在' if result['reused'] else '已导入'}：{result['conversation_count']} 段对话，{result['turn_count']} 轮")
            st.json(result)

dataset_page = st.number_input("数据集页", min_value=1, value=1, step=1)
datasets = request("GET", "/datasets", params={"limit": 20, "offset": (dataset_page - 1) * 20})
st.caption(f"共 {datasets['total']} 个数据集")
if not datasets["items"]:
    st.info("本页没有数据集，请先导入或选择前一页。")
    st.stop()
dataset_id = st.selectbox("数据集", [item["dataset_id"] for item in datasets["items"]])
meta = request("GET", f"/datasets/{dataset_id}")
st.json(meta)
with st.expander("原始数据校验与来源版本"):
    st.json(request("GET", f"/datasets/{dataset_id}/provenance"))
conversation_page = st.number_input("对话页", min_value=1, value=1, step=1)
conversations = request("GET", f"/datasets/{dataset_id}/conversations", params={"limit": 20, "offset": (conversation_page - 1) * 20})
st.caption(f"共 {conversations['total']} 段对话")
if not conversations["items"]:
    st.info("本页没有对话。")
    st.stop()
sample_id = st.selectbox("对话 sample_id", [item["sample_id"] for item in conversations["items"]])
base = f"/datasets/{dataset_id}/conversations/{sample_id}"
session_page = st.number_input("会话页", min_value=1, value=1, step=1)
sessions = request("GET", f"{base}/sessions", params={"limit": 20, "offset": (session_page - 1) * 20})
st.caption(f"共 {sessions['total']} 个会话")
if not sessions["items"]:
    st.info("本页没有会话。")
    st.stop()
session_id = st.selectbox("会话", [item["session_id"] for item in sessions["items"]])
dia_id = st.text_input("精确定位 dia_id（可选，如 D1:1）")
if dia_id:
    st.json(request("GET", f"{base}/turns/{dia_id}"))
else:
    turn_page = st.number_input("轮次页", min_value=1, value=1, step=1)
    turns = request("GET", f"{base}/turns", params={"session_id": session_id, "limit": 20, "offset": (turn_page - 1) * 20})
    st.caption(f"当前会话共 {turns['total']} 轮；保留原始会话时间与英文文本")
    for turn in turns["items"]:
        st.text(f"{turn['dia_id']} · {turn['speaker']}")
        st.caption(f"{turn['session_time']} · {turn['source_id']}")
        st.text(turn["text"])
