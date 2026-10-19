"""Chinese source browser. Every data operation goes through the HTTP API."""

import json

import httpx
import streamlit as st

from locomo_memory.config import load_settings
from locomo_memory.query_ui import render_queries
from locomo_memory.evaluation_ui import render_evaluation


settings = load_settings()
st.set_page_config(page_title="动态对话记忆", layout="wide")
st.title("动态对话记忆 · 原始来源")
st.caption("导入原始英文对话、核对来源并检查原子 Memory 抽取。完整版本支持英文有效证据问答。")


def request(method: str, path: str, **kwargs):
    try:
        response = httpx.request(method, f"{settings.api_url.rstrip('/')}{path}", timeout=60, **kwargs)
        if response.is_error:
            try:
                error = response.json()["error"]
                st.error(f"{error['code']}：{error['message']}")
                if error.get('trace_id'):
                    st.caption(f"失败 Trace：{error['trace_id']}（失败不代表没有证据）")
                    st.json(request('GET', f"/queries/{error['trace_id']}"))
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

st.divider()
st.subheader("原子 Memory 构建与检查")
st.caption("抽取产物可检查；索引、关系和完整版本发布由后续阶段处理。")
if st.button("构建所选对话的 Memory"):
    result = request("POST", "/builds", json={"dataset_id": dataset_id, "sample_id": sample_id})
    st.success(f"构建已接受：{result['build_id']}")
if st.button("刷新构建进度"):
    st.rerun()
build_page = st.number_input("构建版本页", min_value=1, value=1, step=1)
builds = request("GET", "/builds", params={"dataset_id": dataset_id, "sample_id": sample_id, "limit": 20, "offset": (build_page - 1) * 20})
st.caption(f"当前对话共 {builds['total']} 个构建版本")
if builds["items"]:
    build_id = st.selectbox("构建版本", [item["build_id"] for item in builds["items"]])
    build = request("GET", f"/builds/{build_id}")
    labels = {"queued": "等待抽取", "running": "构建中", "failed": "抽取失败，可显式重试", "interrupted": "上次运行已中断，可显式重试", "extracted": "抽取结束，待索引与关系阶段", "indexed": "已建立索引，待关系阶段", "related": "关系与投影已保存，待完整版本发布", "relations_failed": "关系阶段失败，可显式重试", "index_failed": "索引失败，Memory 仍可检查", "complete": "完整版本"}
    st.write(f"状态：{labels.get(build['status'], build['status'])} · 阶段 {build['phase']}")
    progress = build["progress"]
    st.progress((progress["succeeded"] + progress["failed"]) / max(progress["total"], 1), text=f"片段 {progress['total']}，成功 {progress['succeeded']}，失败/中断 {progress['failed']}，待处理 {progress['pending']}")
    if not build["query_ready"]:
        st.info("此版本只供检查，不是可回答完整记忆库问题的版本。")
    if build["phase"] == "extraction" and build["status"] in {"failed", "interrupted"} and st.button("仅重试失败或中断片段"):
        request("POST", f"/builds/{build_id}/retry")
        st.rerun()
    with st.expander("版本、配置与模型调用记录"):
        st.json(build)
    fragment_page = st.number_input("片段页", min_value=1, value=1, step=1)
    fragments = request("GET", f"/builds/{build_id}/fragments", params={"limit": 20, "offset": (fragment_page - 1) * 20})
    st.dataframe([{key: fragment[key] for key in ("ordinal", "status", "attempts", "error_code", "error_message", "no_facts_reason")} for fragment in fragments["items"]], hide_index=True)
    memory_page = st.number_input("Memory 页", min_value=1, value=1, step=1)
    memories = request("GET", f"/builds/{build_id}/memories", params={"limit": 20, "offset": (memory_page - 1) * 20})
    st.caption(f"已保存 {memories['total']} 条原子 Memory（含部分成功产物）")
    for memory in memories["items"]:
        st.text(memory["content"])
        st.caption(f"{memory['memory_id']} · {memory['memory_type']} · {memory['statement_type']} · {memory['polarity']} · {memory['state_key']}")
        with st.expander(f"Memory 时间与来源：{memory['memory_id']}"):
            st.json(memory["time"])
            for source_id in memory["source_ids"]:
                source_dataset, source_sample, source_dia = source_id.split("/")
                source = request("GET", f"/datasets/{source_dataset}/conversations/{source_sample}/turns/{source_dia}")
                st.caption(f"{source_id} · {source['speaker']} · {source['session_time']}")
                st.text(source["text"])

    st.subheader("初始混合检索候选检查")
    st.caption("英文检索；当前仅展示候选、通道排名与分析回退，不生成最终答案。")
    indexable = build["status"] in {"extracted", "indexed", "index_failed"} or (build["status"] == "interrupted" and build["phase"] == "indexing")
    if st.button("建立或重试混合检索索引", disabled=not indexable):
        request("POST", f"/builds/{build_id}/index")
        st.rerun()
    if build["status"] in {"indexed", "index_failed"}:
        with st.expander("索引版本、模型与长度政策"):
            st.json(request("GET", f"/builds/{build_id}/index"))
    question = st.text_input("英文问题（候选检查）", key="candidate_question")
    if st.button("检查 BM25 / Dense / RRF 候选", disabled=build["status"] not in {"indexed", "related", "complete"}):
        st.session_state["candidate_result"] = request("POST", "/candidate-queries", json={"build_id": build_id, "question": question})
    result = st.session_state.get("candidate_result")
    if result and result["build_id"] == build_id:
        st.caption(f"候选记录 {result['query_id']} · 构建 {result['build_id']} · 索引 {result['index_fingerprint']}")
        st.text(result["question"])
        if result["analysis"]["status"] == "fallback":
            st.info(f"问题分析失败，继续检索原问题：{result['analysis']['error_code']}")
        with st.expander("问题分析与实际检索配置"):
            st.json({"analysis": result["analysis"], "config": result["config"], "token_budget_method": result["token_budget_method"]})
        if result["initial_truncated"]:
            st.warning("候选已按预算截断：" + ", ".join(result["truncation_reasons"]))
        for channel in ("bm25", "dense"):
            st.write(f"{channel} 通道排名")
            st.dataframe(result["channels"][channel], hide_index=True)
        st.write("RRF 融合后的初始 Memory")
        for candidate in result["initial_candidates"]:
            memory = candidate["memory"]
            st.text(memory["content"])
            st.caption(f"{memory['memory_id']} · ranks={candidate['channel_ranks']} · RRF={candidate['rrf_score']:.6f}")
            with st.expander(f"候选来源：{memory['memory_id']}"):
                for source_id in memory["source_ids"]:
                    source_dataset, source_sample, source_dia = source_id.split("/")
                    source = request("GET", f"/datasets/{source_dataset}/conversations/{source_sample}/turns/{source_dia}")
                    st.caption(f"{source_id} · {source['session_time']}")
                    st.text(source["text"])

    st.subheader("历史关系与 Current State")
    relation_retry = build["status"] in {"indexed", "relations_failed"} or (build["status"] == "interrupted" and build["phase"] == "relations")
    if st.button("构建或重试历史关系", disabled=not relation_retry):
        request("POST", f"/builds/{build_id}/relations")
        st.rerun()
    if build["phase"] in {"relations", "complete"}:
        phase = request("GET", f"/builds/{build_id}/relation-progress")
        st.json(phase)
        task_page = st.number_input("关系任务页", min_value=1, value=1, step=1)
        tasks = request("GET", f"/builds/{build_id}/relation-tasks", params={"limit": 20, "offset": (task_page - 1) * 20})
        st.dataframe([{key: task[key] for key in ("ordinal", "status", "attempts", "truncated_count", "error_code")} for task in tasks["items"]], hide_index=True)
    if build["status"] in {"related", "complete"}:
        state = request("GET", f"/builds/{build_id}/current-state")
        st.caption(f"已知状态截止：{state['cutoff_source_time']}（不代表此后的现实变化）")
        with st.expander("当前候选、历史、事件、计划及条件/冲突说明"):
            st.json(state)
        if build["status"] == "related":
            if st.button("从历史与关系重算投影"):
                request("POST", f"/builds/{build_id}/current-state/rebuild")
                st.rerun()
            if st.button("校验并发布为完整构建版本"):
                request("POST", f"/builds/{build_id}/publish")
                st.rerun()
        else:
            st.caption("完整版本已固定，问答始终使用所选版本。")
            st.json(request("GET", "/versions/pin", params={"dataset_id": dataset_id, "sample_id": sample_id}))
        relation_page = st.number_input("历史关系页", min_value=1, value=1, step=1)
        relation_rows = request("GET", f"/builds/{build_id}/relations", params={"limit": 20, "offset": (relation_page - 1) * 20})
        st.caption(f"共 {relation_rows['total']} 条判断（含明确未确定）")
        if relation_rows["items"]:
            selected_relation = st.selectbox("关系来源检查", relation_rows["items"], format_func=lambda item: f"{item['label']} · {item['relation_id']}")
            st.json(selected_relation)
            for endpoint in ("old_memory_id", "new_memory_id"):
                st.json(request("GET", f"/builds/{build_id}/memories/{selected_relation[endpoint]}"))
            with st.expander("双方原始证据"):
                for source_id in selected_relation["source_ids"]:
                    source_dataset, source_sample, source_dia = source_id.split("/")
                    source = request("GET", f"/datasets/{source_dataset}/conversations/{source_sample}/turns/{source_dia}")
                    st.caption(f"{source_id} · {source['session_time']}")
                    st.text(source["text"])
        if result and result["build_id"] == build_id:
            if st.button("扩展当前候选的相关历史"):
                st.session_state["expanded_result"] = request("POST", "/candidate-expansions", json={"query_id": result["query_id"]})
            expanded = st.session_state.get("expanded_result")
            if expanded and expanded["query_id"] == result["query_id"]:
                st.caption(f"初始 {len(expanded['initial_candidates'])} · 补充 {len(expanded['added_candidates'])} · 合并 {len(expanded['candidates'])}")
                if expanded["truncated"]:
                    st.warning("相关历史存在截断：" + ", ".join(expanded["truncation_reasons"]))
                for candidate in expanded["candidates"]:
                    st.text(candidate["memory"]["content"])
                    with st.expander(f"扩展入口与来源：{candidate['memory']['memory_id']}"):
                        st.json({"origins": candidate["origins"], "source_ids": candidate["memory"]["source_ids"]})

if builds["items"]:
    from locomo_memory.version_ui import render_version

    render_version(request, build)
    render_queries(request, dataset_id, sample_id, build)

render_evaluation(request, dataset_id)
