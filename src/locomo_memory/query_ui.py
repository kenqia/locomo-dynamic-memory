"""Question, source citation and Trace views using backend HTTP only."""

import streamlit as st


def render_queries(request, dataset_id, sample_id, build):
    st.subheader("有效证据问答")
    st.caption("仅支持英文问题；默认现在指对话截止时间。历史问答不会修改全局状态。")
    question = st.text_area("英文问题", key="effective_question")
    dated = st.checkbox("指定历史或未来日期", key="query_dated")
    requested_date = st.date_input("问题日期", key="query_date", disabled=not dated)
    if st.button("解析有效证据并回答", disabled=not build["query_ready"]):
        payload = {"dataset_id": dataset_id, "sample_id": sample_id, "build_id": build["build_id"], "question": question}
        if dated:
            payload["requested_date"] = requested_date.isoformat()
        st.session_state["effective_result"] = request("POST", "/queries", json=payload)
    trace_id = st.text_input("查看已有 Trace ID（含失败记录）", key="query_trace_id")
    if st.button("读取问答 Trace", disabled=not trace_id):
        st.session_state["effective_result"] = request("GET", f"/queries/{trace_id}")
    trace = st.session_state.get("effective_result")
    if not trace or trace["build_id"] != build["build_id"]:
        return
    st.caption(f"Trace {trace['trace_id']} · 固定构建 {trace['build_id']}")
    if trace["outcome"] == "failed":
        st.error(f"问答执行失败：{trace['error']['code']}。失败不代表没有证据。")
    else:
        labels = {"sufficient": "证据支持", "conflict": "证据冲突", "insufficient": "证据不足"}
        st.write(labels[trace["answer"]["status"]])
        st.text(trace["answer"]["answer"])
        st.caption(f"已知证据截止：{trace['time']['cutoff_source_time']}；不能确认之后的现实状态。")
        for citation in trace["answer"]["citations"]:
            with st.expander(f"回答引用：{citation['memory_id']}"):
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
