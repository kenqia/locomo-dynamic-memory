"""Optional graph/source inspector; only the backend accesses SQLite."""
import json

import streamlit as st


DISPLAY_EDGE_LIMIT = 300


def graph_dot(graph):
    quote = lambda value: json.dumps(str(value), ensure_ascii=False)
    lines = ['digraph Memory {', 'rankdir=LR;']
    for node in graph['nodes']:
        shape = 'box' if node['kind'] == 'Memory' else 'ellipse'
        status = node.get('status', '')
        color = 'red' if status == 'conflict' else 'gray' if status in ('superseded', 'historical') else 'black'
        lines.append(f'{quote(node["id"])} [label={quote(node["label"][:90])},shape={shape},color={quote(color)}];')
    for edge in graph['edges'][:DISPLAY_EDGE_LIMIT]:
        lines.append(f'{quote(edge["source"])} -> {quote(edge["target"])} [label={quote(edge["type"])}];')
    return '\n'.join(lines + ['}'])


def render_bonus(request, build):
    with st.expander('Bonus · 状态演化与 Graph Memory', expanded=False):
        if not st.checkbox('开启只读图浏览', value=False, key='m5_graph_enabled'):
            return
        build_id = build['build_id']
        metadata = request('GET', f'/builds/{build_id}/bonus/graph')
        if not metadata['entities']:
            st.info('此版本没有实体记忆。')
            return
        entity = st.selectbox('实体', metadata['entities'], key='m5_graph_entity')
        depth = st.slider('图浏览深度', 1, 2, 2, key='m5_graph_depth')
        dated = st.checkbox('按有效日期筛选', key='m5_graph_dated')
        params = dict(root='entity:' + entity, depth=depth)
        if dated:
            params['at'] = st.date_input('有效日期', key='m5_graph_date').isoformat()
        graph = request('GET', f'/builds/{build_id}/bonus/graph', params=params)
        st.caption('结构边表示字段归属；图连通不证明事实正确或当前有效。')
        if len(graph['edges']) > DISPLAY_EDGE_LIMIT:
            st.caption(f'邻域含 {len(graph["edges"])} 条边；画布和表格仅显示前 {DISPLAY_EDGE_LIMIT} 条，完整邻域保留在图 JSON 下载中。')
        st.graphviz_chart(graph_dot(graph))
        if graph['truncated']:
            st.warning('图达到节点上限，仅显示部分邻域。')
        nodes = {n['id']: n for n in graph['nodes']}
        chosen = st.selectbox('查看节点及原文来源', list(nodes),
                              format_func=lambda key: nodes[key]['label'], key='m5_graph_node')
        node = nodes[chosen]
        if node['kind'] == 'Memory':
            st.json(node['memory'])
            for sid in node['memory']['source_ids']:
                source = request('GET', f'/datasets/{node["memory"]["dataset_id"]}/conversations/{node["memory"]["sample_id"]}/turns/{sid.rsplit("/", 1)[-1]}')
                st.text(f'{source["speaker"]} · {source["dia_id"]} · {source["session_time"]}')
                st.text(source['text'])
        elif node['kind'] == 'Source Turn':
            st.json(node['source'])
        st.dataframe(graph['edges'][:DISPLAY_EDGE_LIMIT], use_container_width=True)
        st.download_button('下载所选图 JSON', json.dumps(graph, ensure_ascii=False, indent=2),
                           file_name=f'{build_id}-graph.json', mime='application/json', key='m5_graph_download')
        memories = [n['memory'] for n in graph['nodes'] if n['kind'] == 'Memory']
        dimensions = sorted({m['state_dimension'] for m in memories if m['entity_id'] == entity})
        if dimensions:
            dimension = st.selectbox('状态维度', dimensions, key='m5_timeline_dimension')
            timeline = request('GET', f'/builds/{build_id}/bonus/timeline',
                               params=dict(entity=entity, dimension=dimension))
            st.caption('来源顺序不代表当前有效；适用性仍须结合查询、时间和条件判断。')
            st.dataframe([dict(content=m['content'], nature=m['statement_type'],
                               polarity=m['polarity'], memory_id=m['memory_id'])
                          for m in timeline['memories']], use_container_width=True)
            st.json(timeline['relations'])
