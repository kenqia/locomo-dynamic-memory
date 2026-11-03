"""Question, source citation and Trace views using backend HTTP only."""

import streamlit as st


def render_queries(request, dataset_id, sample_id, build):
    st.subheader("提出问题")
    st.caption("当前支持英文问题。日期留空时，系统采用所选对话的证据截止时间。")
    strategy_columns = st.columns([1, 2.35], gap="large", vertical_alignment="bottom")
    strategy = strategy_columns[0].selectbox(
        "问答策略",
        ["dynamic", "dynamic_raw_fallback"],
        format_func=lambda value: "Dynamic" if value == "dynamic" else "Dynamic + 原文兜底",
        key="query_strategy",
    )
    strategy_columns[1].caption(
        "Dynamic 使用结构化 Memory；原文兜底只在结构化证据不足时补充有限原始轮次。"
    )
    input_columns = st.columns([2.4, 1], gap="large")
    question = input_columns[0].text_input(
        "英文问题",
        placeholder="例如：Where does Alex live now?",
        key="effective_question",
    )
    requested_date = input_columns[1].text_input(
        "指定日期，可留空",
        placeholder="YYYY-MM-DD，例如 2023-05-01",
        key="query_date_text",
    ).strip()
    if st.button(
        "分析证据并回答",
        disabled=not build["query_ready"],
        type="primary",
        use_container_width=True,
    ):
        if not question.strip():
            st.warning("请先输入一个英文问题。")
        else:
            payload = {"dataset_id": dataset_id, "sample_id": sample_id, "build_id": build["build_id"], "question": question,
                       "strategy": strategy}
            if requested_date:
                payload["requested_date"] = requested_date
            st.session_state["effective_result"] = request("POST", "/queries", json=payload)
    with st.expander("读取已有问答记录"):
        trace_id = st.text_input("Trace ID", key="query_trace_id")
        if st.button("读取 Trace", key="load_query_trace"):
            if not trace_id:
                st.warning("请先输入 Trace ID。")
            else:
                st.session_state["effective_result"] = request("GET", f"/queries/{trace_id}")
    trace = st.session_state.get("effective_result")
    if not trace or trace["build_id"] != build["build_id"]:
        return
    st.subheader("回答")
    st.caption(f"Trace {trace['trace_id']} · 固定构建 {trace['build_id']}")
    st.caption("此记录的策略：" + trace.get("strategy", "dynamic"))
    if trace.get("strategy_recovery"):
        st.caption("动态解析输出校验失败，已尝试有界原文备用策略；原失败与调用用量保留在 Trace。")
    if trace["outcome"] == "failed":
        st.error(f"问答执行失败：{trace['error']['code']}。失败不代表没有证据。")
    else:
        labels = {"sufficient": "证据支持", "conflict": "证据冲突", "insufficient": "证据不足"}
        with st.chat_message("assistant"):
            st.write(labels[trace["answer"]["status"]])
            st.text(trace["answer"]["answer"])
            if trace["answer"].get("explanation"):
                st.caption(trace["answer"]["explanation"])
            if trace.get("answer_boundary"):
                st.caption(trace["answer_boundary"]["text"])
            st.caption(f"已知证据截止：{trace['time']['cutoff_source_time']}；不能确认之后的现实状态。")
        for citation in trace["answer"]["citations"]:
            with st.expander(f"回答引用：{citation['memory_id'] or '原始对话'}"):
                for source_id in citation["source_ids"]:
                    ds, sample, dia_id = source_id.split("/")
                    source = request("GET", f"/datasets/{ds}/conversations/{sample}/turns/{dia_id}")
                    st.caption(f"{source_id} · {source['session_time']}")
                    st.text(source["text"])
        with st.expander("初始候选、历史扩展、有效集合与排除理由"):
            st.json({"initial": trace["initial"], "expanded": trace["expanded"], "resolution": trace["resolution"],
                     "effective_memories": trace["effective_memories"], "evidence_budget": trace["evidence_budget"]})
    with st.expander("完整 Trace、实际配置、模型调用及用量"):
        st.json(trace)
