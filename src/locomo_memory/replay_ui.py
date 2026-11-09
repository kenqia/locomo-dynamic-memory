"""Offline Streamlit replay: file reads only, no model or database operations."""

import json
import os
from pathlib import Path

import streamlit as st

from locomo_memory.m5_compression import pack, expand
from locomo_memory.m5_graph import neighborhood
from locomo_memory.release_viewer import DEMO, ExportCatalog

st.set_page_config(page_title="LoCoMo · Offline Replay", layout="wide")
st.title("LoCoMo · 只读离线演示")
manifest = Path(os.environ.get("LOCOMO_REPLAY_MANIFEST", str(DEMO / "manifest.json")))
directory = os.environ.get("LOCOMO_REPLAY_DIRECTORY")
try:
    catalog = ExportCatalog(manifest, Path(directory) if directory else None)
    sample_id = st.selectbox("选择数据 / Build", list(catalog.entries))
    bundle = catalog.read(sample_id)
except (ValueError, OSError, KeyError):
    st.error("数据缺失或完整性检查失败。请运行 validate-six-exports 检查清单和目录。")
    st.stop()

st.caption(f"{catalog.manifest['kind']} · Build {bundle.build.build_id} · SHA {catalog.entries[sample_id]['sha256']}")
if catalog.manifest["kind"] == "Synthetic / Offline Replay":
    st.warning("Synthetic / Offline Replay：合成来源与预录回答，非真实 LoCoMo 模型得分。无模型调用。")
else:
    st.info("Controlled MemoryExport：仅浏览受控原始导出；没有预录问答时不会生成回答。")
columns = st.columns(3)
columns[0].metric("Memory", len(bundle.memories))
columns[1].metric("MemoryRelation", len(bundle.relations))
columns[2].metric("Source Turn", len(bundle.sources))

st.subheader("Memory 与来源")
mid = st.selectbox("选择 Memory", [m.memory_id for m in bundle.memories])
memory = next(m for m in bundle.memories if m.memory_id == mid)
st.json(memory.model_dump(mode="json"))
st.subheader("历史状态与关系")
st.json(bundle.projection.model_dump(mode="json"))
related = [r for r in bundle.relations if mid in (r.old_memory_id, r.new_memory_id)]
st.json([r.model_dump(mode="json") for r in related[:50]])
st.caption("最多展示与所选 Memory 相连的前 50 条关系；完整关系保留在 JSON 导出。关系标签是模型产物，非人工真值。")

st.subheader("Graph 浏览（显式开启）")
if st.checkbox("显示有来源的 Graph", value=False):
    graph = neighborhood(bundle, [mid], depth=2, max_nodes=80)
    labels = {n["id"]: n["kind"] for n in graph["nodes"]}
    # IDs and edge labels are escaped as JSON strings in Graphviz DOT.
    lines = ["digraph G {", 'graph [rankdir="LR"];']
    for node_id, label in labels.items():
        lines.append(f"{json.dumps(node_id)} [label={json.dumps(label + ': ' + node_id[-14:])}];")
    for edge in graph["edges"]:
        if edge["source"] in labels and edge["target"] in labels:
            lines.append(f"{json.dumps(edge['source'])} -> {json.dumps(edge['target'])} [label={json.dumps(edge['type'])}];")
    st.graphviz_chart("\n".join(lines + ["}"]))
    st.json(graph)

st.subheader("Source Turn")
sources = {s.source_id: s for s in bundle.sources}
sid = st.selectbox("来源 ID", list(sources))
st.text(sources[sid].text)
st.caption(f"{sources[sid].dia_id} · {sources[sid].session_time}")

st.subheader("预录 Question / Citations / Query Trace")
replays = catalog.manifest.get("replays", [])
if replays:
    replay_name = st.selectbox("选择预录问题", [r["name"] for r in replays])
    replay = next(r for r in replays if r["name"] == replay_name)
    # Replay file is confined just like the export; never follow arbitrary URLs.
    replay_path = (catalog.directory / replay["file"]).resolve()
    if not replay_path.is_relative_to(catalog.directory):
        st.error("Invalid replay path")
        st.stop()
    trace = json.loads(replay_path.read_text(encoding="utf-8"))
    st.text(trace["question"])
    if trace["outcome"] == "failed":
        st.error(f"预录失败 Trace：{trace['error']['code']}（没有发送请求）")
    else:
        st.text(trace["answer"]["answer"])
        st.json(trace["answer"]["citations"])
    st.json(trace)
else:
    st.info("此清单没有预录问题。只读模式不会创建新的回答。")

st.subheader("评测对照（Real Experimental Result，冻结汇总）")
st.caption("与上面的合成回放分开：Level E 类别1–4，完整分母301/臂；失败记零，区间跨零，未证明 Dynamic 稳定优于 Hybrid。")
st.table([{"strategy": "Hybrid", "F1": 0.402606, "n": 301},
          {"strategy": "Dynamic", "F1": 0.409151, "n": 301}])
st.caption("来源：docs/m5-development/LEVEL_E_RESULTS_V1.md；类别5字面拒答另报。测试已曝光，禁止重新调参后称独立测试。")
if st.checkbox("演示可逆分组（默认关闭，非 QA 增益）", value=False):
    memories = [m.model_dump(mode="json") for m in bundle.memories]
    grouped = pack(memories)
    st.json(grouped)
    st.write("无损展开校验", expand(grouped["package"]) == memories)
st.download_button("导出 Memory JSON", catalog.path(sample_id).read_bytes(), file_name=f"{sample_id}.json", mime="application/json")
