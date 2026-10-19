"""HTTP-only phase recovery and complete collection download controls."""
import json

import streamlit as st


def render_version(request, build):
    st.subheader("恢复与完整版本导出")
    if build["status"] in {"failed", "interrupted", "index_failed", "relations_failed"}:
        st.caption(f"只恢复 {build['phase']} 阶段；成功片段和已完成比较会保留。配置变化时请新建版本。")
        if st.button("显式重试当前失败或中断阶段", key="version_phase_retry"):
            request("POST", f"/builds/{build['build_id']}/retry-phase")
            st.rerun()
    if build["status"] != "complete":
        st.info("此版本的部分产物只供检查。完整 JSON 下载在校验发布后开放。")
        return
    st.caption(f"下载当前选择的完整版本 {build['build_id']}，包含全部 Memory、原始来源、关系、投影和索引身份。")
    if st.button("准备所选版本 JSON", key="prepare_version_export"):
        bundle = request("GET", f"/builds/{build['build_id']}/export")
        st.session_state["version_export"] = bundle
    bundle = st.session_state.get("version_export")
    if bundle and bundle["build"]["build_id"] == build["build_id"]:
        st.download_button("下载完整 Memory JSON", data=json.dumps(bundle, ensure_ascii=False, indent=2),
                           file_name=f"memory-{build['build_id']}.json", mime="application/json", key="download_version_export")
