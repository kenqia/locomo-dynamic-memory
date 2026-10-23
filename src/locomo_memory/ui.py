"""Linear Streamlit workflow. Every data operation goes through the HTTP API."""

import json

import httpx
import streamlit as st

from locomo_memory.build_progress import summarize_build_progress
from locomo_memory.config import load_settings
from locomo_memory.evaluation_ui import render_evaluation
from locomo_memory.query_ui import render_queries
from locomo_memory.ui_theme import (
    apply_app_theme,
    render_context,
    render_page_header,
    render_workflow_header,
)
from locomo_memory.version_ui import render_version


settings = load_settings()
st.set_page_config(
    page_title="动态对话记忆",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_app_theme()


def request(method: str, path: str, **kwargs):
    try:
        response = httpx.request(method, f"{settings.api_url.rstrip('/')}{path}", timeout=60, **kwargs)
        if response.is_error:
            try:
                error = response.json()["error"]
                st.error(f"{error['code']}：{error['message']}")
                if error.get("trace_id"):
                    st.caption(f"失败 Trace：{error['trace_id']}。该记录可用于检查失败阶段。")
            except (ValueError, KeyError, TypeError):
                st.error("后端返回了无法识别的错误。")
            st.stop()
        return response.json()
    except httpx.HTTPError:
        st.error("无法连接后端，请先启动 FastAPI 服务。")
        st.stop()


for key, default in (
    ("workflow_step", 1),
    ("workspace_dataset_id", None),
    ("workspace_sample_id", None),
    ("workspace_build_id", None),
):
    st.session_state.setdefault(key, default)


def go_to(step: int) -> None:
    st.session_state["workflow_step"] = step
    st.rerun()


def activate_dataset(dataset_id: str) -> None:
    st.session_state["workspace_dataset_id"] = dataset_id
    st.session_state["workspace_sample_id"] = None
    st.session_state["workspace_build_id"] = None
    st.session_state.pop("candidate_result", None)
    st.session_state.pop("expanded_result", None)
    st.session_state.pop("effective_result", None)
    st.session_state["workflow_step"] = 2
    st.rerun()


def activate_conversation(sample_id: str) -> None:
    st.session_state["workspace_sample_id"] = sample_id
    st.session_state["workspace_build_id"] = None
    st.session_state.pop("candidate_result", None)
    st.session_state.pop("expanded_result", None)
    st.session_state.pop("effective_result", None)
    st.session_state["workflow_step"] = 3
    st.rerun()


def activate_build(build_id: str) -> None:
    st.session_state["workspace_build_id"] = build_id
    st.session_state.pop("candidate_result", None)
    st.session_state.pop("expanded_result", None)
    st.session_state.pop("effective_result", None)
    st.rerun()


def card_title(title: str, copy: str) -> None:
    st.markdown(
        f'<div class="dm-card-title">{title}</div><div class="dm-card-copy">{copy}</div>',
        unsafe_allow_html=True,
    )


def inline_title(title: str, copy: str) -> None:
    st.markdown(
        f'<div class="dm-inline-title"><strong>{title}</strong><span>{copy}</span></div>',
        unsafe_allow_html=True,
    )


def render_upload_page() -> None:
    st.markdown('<span class="dm-page-upload-marker"></span>', unsafe_allow_html=True)
    render_page_header(
        "01 · DATA SOURCE",
        "上传一份对话数据",
        "上传本地 LoCoMo JSON，校验通过后进入对话选择页。",
    )
    datasets = request("GET", "/datasets", params={"limit": 6, "offset": 0})
    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown('<span class="dm-upload-panel-marker"></span>', unsafe_allow_html=True)
            card_title("上传本地文件", "上传合成案例、课程副本或团队数据，文件需符合 LoCoMo JSON 结构。")
            uploaded = st.file_uploader("选择 JSON 文件", type=["json"], label_visibility="collapsed")
            metadata_columns = st.columns(2, gap="small")
            version = metadata_columns[0].text_input("数据版本", value="local-v1")
            license_name = metadata_columns[1].text_input("许可证", value="CC-BY-NC-4.0")
            if st.button(
                "上传并继续",
                disabled=uploaded is None,
                type="primary",
                use_container_width=True,
                key="upload_and_continue",
            ):
                try:
                    json.loads(uploaded.getvalue())
                except (ValueError, UnicodeError):
                    st.error("文件需要使用 UTF-8 编码，并包含有效 JSON。")
                else:
                    result = request(
                        "POST",
                        "/imports/file",
                        files={"file": (uploaded.name, uploaded.getvalue(), "application/json")},
                        data={"version": version, "license": license_name},
                    )
                    activate_dataset(result["dataset_id"])
    with right:
        with st.container(border=True):
            st.markdown('<span class="dm-upload-panel-marker"></span>', unsafe_allow_html=True)
            card_title("官方 LoCoMo", "导入固定原件，并校验版本、许可与文件摘要。")
            if st.button("导入官方 LoCoMo", use_container_width=True, key="import_official"):
                result = request("POST", "/imports/official")
                activate_dataset(result["dataset_id"])
            if datasets["items"]:
                st.divider()
                card_title("已有数据", "直接继续，无需重复上传。")
                for dataset in datasets["items"]:
                    label = (
                        f"{dataset['version']} · {dataset['conversation_count']} 段对话"
                        f" · {dataset['turn_count']} 轮"
                    )
                    if st.button(
                        label,
                        key=f"resume_dataset_{dataset['dataset_id']}",
                        help=dataset["dataset_id"],
                        use_container_width=True,
                    ):
                        activate_dataset(dataset["dataset_id"])


def render_conversation_page(dataset_id: str) -> None:
    st.markdown('<span class="dm-page-conversation-marker"></span>', unsafe_allow_html=True)
    meta = request("GET", f"/datasets/{dataset_id}")
    render_page_header(
        "02 · CONVERSATION",
        "选择要处理的对话",
        "选择一段对话进入构建页，后续操作始终绑定该对话。",
    )
    render_context(dataset_id=dataset_id)
    summary = st.columns(3)
    summary[0].metric("对话数量", meta["conversation_count"])
    summary[1].metric("原始轮次", meta["turn_count"])
    summary[2].metric("数据版本", meta["version"])

    conversations = request(
        "GET",
        f"/datasets/{dataset_id}/conversations",
        params={"limit": 100, "offset": 0},
    )
    st.subheader("对话列表")
    for conversation in conversations["items"]:
        with st.container(border=True):
            st.markdown('<span class="dm-conversation-card-marker"></span>', unsafe_allow_html=True)
            content, action = st.columns([3.2, 1], gap="large", vertical_alignment="center")
            with content:
                card_title(
                    conversation["sample_id"],
                    f"{conversation['speaker_a']} 与 {conversation['speaker_b']} · "
                    f"{conversation['session_count']} 个会话 · {conversation['turn_count']} 个轮次",
                )
            with action:
                if st.button(
                    f"使用 {conversation['sample_id']}",
                    key=f"choose_conversation_{conversation['sample_id']}",
                    type="primary" if len(conversations["items"]) == 1 else "secondary",
                    use_container_width=True,
                ):
                    activate_conversation(conversation["sample_id"])
    navigation = st.columns([1, 3], gap="large", vertical_alignment="center")
    if navigation[0].button("返回上传页", key="conversation_back", use_container_width=True):
        go_to(1)
    navigation[1].caption("选择后进入记忆构建，原始对话保持只读。")


BUILD_LABELS = {
    "queued": "等待开始",
    "running": "正在抽取",
    "failed": "抽取失败",
    "interrupted": "执行中断",
    "extracted": "Memory 已生成",
    "indexed": "检索索引已建立",
    "related": "关系与当前状态已生成",
    "relations_failed": "关系构建失败",
    "index_failed": "索引构建失败",
    "complete": "完整版本已发布",
}


def render_source_preview(dataset_id: str, sample_id: str) -> None:
    base = f"/datasets/{dataset_id}/conversations/{sample_id}"
    turns = request("GET", f"{base}/turns", params={"limit": 6, "offset": 0})
    with st.expander("检查原始对话", expanded=False):
        st.caption(f"当前显示前 {len(turns['items'])} 个轮次，共 {turns['total']} 个轮次。")
        for turn in turns["items"]:
            with st.container(border=True):
                st.markdown(f"**{turn['speaker']}** · `{turn['dia_id']}`")
                st.write(turn["text"])
                st.caption(turn["session_time"])
        dia_id = st.text_input("按 dia_id 定位原文", placeholder="例如 D1:1", key="source_dia_id")
        if st.button("读取这一轮", key="load_source_turn"):
            if not dia_id:
                st.warning("请先输入 dia_id。")
            else:
                turn = request("GET", f"{base}/turns/{dia_id}")
                st.markdown(f"**{turn['speaker']}** · `{turn['dia_id']}`")
                st.write(turn["text"])
                st.caption(turn["session_time"])


def render_candidate_diagnostics(build: dict, *, bordered: bool = True) -> None:
    ready = build["status"] in {"indexed", "related", "complete"}
    with st.container(border=bordered):
        inline_title("检索诊断", "输入英文问题，查看 BM25、Dense 与 RRF 候选；只执行检索。")
        controls = st.columns([4, 1], gap="medium", vertical_alignment="bottom")
        question = controls[0].text_input(
            "检索问题",
            placeholder="例如：Where does Alex live?",
            key="candidate_question",
            label_visibility="collapsed",
        )
        if controls[1].button(
            "运行检索诊断",
            disabled=not ready,
            key="run_candidate_query",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning("请先输入一个英文问题。")
            else:
                st.session_state["candidate_result"] = request(
                    "POST",
                    "/candidate-queries",
                    json={"build_id": build["build_id"], "question": question},
                )
        if not ready:
            st.caption("完成检索索引后即可运行诊断。")
        result = st.session_state.get("candidate_result")
        if not result or result["build_id"] != build["build_id"]:
            return
        st.caption(f"Query {result['query_id']} · 初始候选 {len(result['initial_candidates'])} 条")
        for candidate in result["initial_candidates"]:
            memory = candidate["memory"]
            with st.container(border=True):
                st.write(memory["content"])
                st.caption(f"RRF {candidate['rrf_score']:.6f} · {memory['memory_id']}")
        if st.button("扩展相关历史", key="expand_candidate_history"):
            st.session_state["expanded_result"] = request(
                "POST",
                "/candidate-expansions",
                json={"query_id": result["query_id"]},
            )
        expanded = st.session_state.get("expanded_result")
        if expanded and expanded["query_id"] == result["query_id"]:
            st.success(
                f"初始 {len(expanded['initial_candidates'])} 条，补充 {len(expanded['added_candidates'])} 条，"
                f"合并后 {len(expanded['candidates'])} 条。"
            )


def render_build_details(build: dict) -> None:
    build_id = build["build_id"]
    with st.popover("构建详情", use_container_width=True):
        fragments = request("GET", f"/builds/{build_id}/fragments", params={"limit": 20, "offset": 0})
        st.markdown("**片段处理**")
        st.dataframe(
            [
                {key: fragment[key] for key in ("ordinal", "status", "attempts", "error_code", "no_facts_reason")}
                for fragment in fragments["items"]
            ],
            hide_index=True,
            use_container_width=True,
        )
        memories = request("GET", f"/builds/{build_id}/memories", params={"limit": 8, "offset": 0})
        st.markdown(f"**Memory 预览 · {memories['total']} 条**")
        for memory in memories["items"]:
            with st.container(border=True):
                st.write(memory["content"])
                st.caption(f"{memory['memory_type']} · {memory['statement_type']} · {memory['state_key']}")
        if build["status"] in {"related", "complete"}:
            state = request("GET", f"/builds/{build_id}/current-state")
            st.markdown("**当前状态投影**")
            st.caption(f"已知证据截止：{state['cutoff_source_time']}")
            st.json(state)
            relations = request("GET", f"/builds/{build_id}/relations", params={"limit": 6, "offset": 0})
            st.markdown(f"**关系预览 · {relations['total']} 条**")
            for relation in relations["items"]:
                with st.expander(f"{relation['label']} · {relation['relation_id']}"):
                    st.write(relation["reason"])
                    st.caption("来源：" + "，".join(relation["source_ids"]))
        with st.expander("版本、配置与模型调用记录"):
            st.json(build)


def render_build_history(builds: dict, active_build_id: str) -> None:
    if len(builds["items"]) <= 1:
        return
    with st.popover("历史构建版本", use_container_width=True):
        st.caption("页面默认使用最新构建。需要复核旧结果时，可在这里显式切换。")
        for item in builds["items"]:
            columns = st.columns([4, 1])
            columns[0].write(f"`{item['build_id']}` · {BUILD_LABELS.get(item['status'], item['status'])}")
            if item["build_id"] == active_build_id:
                columns[1].caption("当前")
            elif columns[1].button("使用", key=f"use_build_{item['build_id']}"):
                activate_build(item["build_id"])


def render_build_page(dataset_id: str, sample_id: str) -> None:
    render_page_header(
        "03 · MEMORY BUILD",
        "构建这段对话的记忆",
        "系统按顺序完成 Memory 抽取、检索索引、历史关系和版本发布。页面只显示当前需要执行的操作。",
    )
    render_context(dataset_id=dataset_id, sample_id=sample_id)
    render_source_preview(dataset_id, sample_id)

    builds = request(
        "GET",
        "/builds",
        params={"dataset_id": dataset_id, "sample_id": sample_id, "limit": 20, "offset": 0},
    )
    active_build_id = st.session_state.get("workspace_build_id")
    active = next((item for item in builds["items"] if item["build_id"] == active_build_id), None)
    if active is None and builds["items"]:
        active = builds["items"][0]
        st.session_state["workspace_build_id"] = active["build_id"]

    if active is None:
        with st.container(border=True):
            card_title("准备就绪", "已确认数据集和对话。开始后，系统会保存构建进度，失败片段可以单独重试。")
            if st.button("开始构建 Memory", type="primary", use_container_width=True, key="start_memory_build"):
                created = request("POST", "/builds", json={"dataset_id": dataset_id, "sample_id": sample_id})
                st.session_state["workspace_build_id"] = created["build_id"]
                st.rerun()
        if st.button("返回对话选择", key="build_back_without_version"):
            go_to(2)
        return

    build = request("GET", f"/builds/{active['build_id']}")
    render_context(build_id=build["build_id"])
    progress = build["progress"]
    relation_progress = None
    if build["phase"] == "relations":
        relation_progress = request("GET", f"/builds/{build['build_id']}/relation-progress")
    progress_summary = summarize_build_progress(build, relation_progress)
    with st.container(border=True):
        status = build["status"]
        if status == "complete":
            status_header = st.columns([1, 3], gap="medium", vertical_alignment="center")
            status_header[0].markdown(
                f'<span class="dm-status">{progress_summary["status_label"]}</span>',
                unsafe_allow_html=True,
            )
            status_header[1].markdown(
                '<div class="dm-build-ready">完整构建版本已经发布，可以开始证据问答。</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<span class="dm-status">{progress_summary["status_label"]}</span>',
                unsafe_allow_html=True,
            )
        st.progress(
            progress_summary["value"],
            text=(
                f"整体构建 {progress_summary['value']:.0%} · "
                f"第 {progress_summary['stage']} / 4 阶段 · {progress_summary['label']}"
            ),
        )
        detail_parts = [
            f"Memory 片段：成功 {progress['succeeded']} / {progress['total']}，"
            f"失败 {progress['failed']}，待处理 {progress['pending']}"
        ]
        if relation_progress is not None:
            relation_counts = relation_progress["progress"]
            detail_parts.append(
                f"关系任务：成功 {relation_counts['succeeded']} / {relation_counts['total']}，"
                f"失败 {relation_counts['failed']}，待处理 {relation_counts['pending']}"
            )
        st.caption(" · ".join(detail_parts))

        if status in {"queued", "running"}:
            st.info("构建正在执行。等待数秒后刷新状态。")
        elif status in {"failed", "interrupted"} and build["phase"] == "extraction":
            st.warning("部分片段尚未完成。重试只处理失败或中断片段。")
            if st.button("重试未完成片段", type="primary", use_container_width=True, key="retry_extraction"):
                request("POST", f"/builds/{build['build_id']}/retry")
                st.rerun()
        elif status in {"extracted", "index_failed"} or (status == "interrupted" and build["phase"] == "indexing"):
            st.info("Memory 已保存。下一步建立 BM25、Dense 和 RRF 检索索引。")
            if st.button("建立检索索引", type="primary", use_container_width=True, key="build_index"):
                request("POST", f"/builds/{build['build_id']}/index")
                st.rerun()
        elif status in {"indexed", "relations_failed"} or (status == "interrupted" and build["phase"] == "relations"):
            st.info("检索索引已就绪。下一步生成历史关系和当前状态投影。")
            if st.button("生成历史关系", type="primary", use_container_width=True, key="build_relations"):
                request("POST", f"/builds/{build['build_id']}/relations")
                st.rerun()
        elif status == "related":
            st.info("关系和状态投影已生成。发布后，这个版本可以用于问答和评测。")
            action_columns = st.columns(2)
            if action_columns[0].button("重新计算当前状态", use_container_width=True, key="rebuild_projection"):
                request("POST", f"/builds/{build['build_id']}/current-state/rebuild")
                st.rerun()
            if action_columns[1].button(
                "校验并发布版本",
                type="primary",
                use_container_width=True,
                key="publish_build",
            ):
                request("POST", f"/builds/{build['build_id']}/publish")
                st.rerun()
        elif status == "complete":
            complete_actions = st.columns([3, 1], gap="medium")
            if complete_actions[0].button(
                "进入证据问答",
                type="primary",
                use_container_width=True,
                key="continue_to_query",
            ):
                go_to(4)
            if complete_actions[1].button(
                "刷新状态",
                use_container_width=True,
                key="refresh_build",
            ):
                st.rerun()
        if status != "complete":
            if st.button("刷新当前状态", use_container_width=True, key="refresh_build"):
                st.rerun()

        st.divider()
        render_candidate_diagnostics(build, bordered=False)
        st.divider()
        has_history = len(builds["items"]) > 1
        controls = st.columns(4 if has_history else 3, gap="medium", vertical_alignment="center")
        with controls[0]:
            render_build_details(build)
        navigation_offset = 1
        if has_history:
            with controls[1]:
                render_build_history(builds, build["build_id"])
            navigation_offset = 2
        if controls[navigation_offset].button(
            "返回对话选择",
            use_container_width=True,
            key="build_back",
        ):
            go_to(2)
        running_build = any(item["status"] in {"queued", "running"} for item in builds["items"])
        if controls[navigation_offset + 1].button(
            "新建一个构建版本",
            use_container_width=True,
            key="new_build",
            disabled=running_build,
        ):
            created = request("POST", "/builds", json={"dataset_id": dataset_id, "sample_id": sample_id})
            activate_build(created["build_id"])


def render_query_page(dataset_id: str, sample_id: str, build: dict) -> None:
    render_page_header(
        "04 · EVIDENCE CHAT",
        "基于固定版本提问",
        "输入英文问题。系统返回答案、证据状态和原始引用，历史问题可以指定日期。",
    )
    render_context(dataset_id=dataset_id, sample_id=sample_id, build_id=build["build_id"])
    render_queries(request, dataset_id, sample_id, build)
    navigation = st.columns(2)
    if navigation[0].button("返回构建页", use_container_width=True, key="query_back"):
        go_to(3)
    if navigation[1].button("进入评测与报告", type="primary", use_container_width=True, key="query_to_report"):
        go_to(5)


def render_report_page(dataset_id: str, sample_id: str, build: dict) -> None:
    render_page_header(
        "05 · EVALUATION REPORT",
        "运行评测并导出报告",
        "使用固定题目和策略创建评测。完成后可下载 JSON、可视化 HTML 报告和完整 Memory 版本。",
    )
    render_context(dataset_id=dataset_id, sample_id=sample_id, build_id=build["build_id"])
    render_evaluation(request, dataset_id)
    st.divider()
    render_version(request, build)
    navigation = st.columns(2)
    if navigation[0].button("返回证据问答", use_container_width=True, key="report_back"):
        go_to(4)
    if navigation[1].button("处理新的数据文件", use_container_width=True, key="report_restart"):
        go_to(1)


step = int(st.session_state["workflow_step"])
dataset_id = st.session_state.get("workspace_dataset_id")
sample_id = st.session_state.get("workspace_sample_id")
build_id = st.session_state.get("workspace_build_id")

if step > 1 and not dataset_id:
    step = 1
    st.session_state["workflow_step"] = 1
if step > 2 and not sample_id:
    step = 2
    st.session_state["workflow_step"] = 2

render_workflow_header(step)

if step == 1:
    render_upload_page()
elif step == 2:
    render_conversation_page(dataset_id)
elif step == 3:
    render_build_page(dataset_id, sample_id)
else:
    builds = request(
        "GET",
        "/builds",
        params={"dataset_id": dataset_id, "sample_id": sample_id, "limit": 20, "offset": 0},
    )
    selected = next((item for item in builds["items"] if item["build_id"] == build_id), None)
    if selected is None and builds["items"]:
        selected = builds["items"][0]
        st.session_state["workspace_build_id"] = selected["build_id"]
    if selected is None or not selected["query_ready"]:
        st.warning("当前对话还没有可用于问答的完整构建版本。")
        if st.button("返回构建页", key="missing_build_back"):
            go_to(3)
    else:
        build = request("GET", f"/builds/{selected['build_id']}")
        if step == 4:
            render_query_page(dataset_id, sample_id, build)
        else:
            render_report_page(dataset_id, sample_id, build)
