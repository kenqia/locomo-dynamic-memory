"""Timeline and Trace inspection through UI and public HTTP boundaries."""
import sys

import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def inspector_app(client, build, monkeypatch, trace=None):
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.evidence_ui import render_memory_inspector, render_trace_inspector
if st.session_state.get('trace'):
    render_trace_inspector(st.session_state['request'], st.session_state['build'], st.session_state['trace'])
else:
    render_memory_inspector(st.session_state['request'], st.session_state['build'])
''', default_timeout=20)
    calls = []

    def request(method, path, **kwargs):
        calls.append((method, path))
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    app.session_state['request'] = request
    app.session_state['build'] = build
    app.session_state['trace'] = trace
    return app, calls


def test_timeline_preserves_unknown_event_time_and_opens_exact_source(settings, sample, monkeypatch):
    model = DeepSeekModel(settings, api_key='synthetic-inspector', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        _, build_id = complete_build(client, sample)
        build = client.get(f'/builds/{build_id}').json()
        app, calls = inspector_app(client, build, monkeypatch)
        app.run()
        assert not app.exception
        assert not app.dataframe
        assert app.radio(key=f'console_memory_{build_id}').options == ['Alex lives in Paris.', 'Alex lives in Rome.']
        assert any('事件时间：unknown → unknown' == item.value for item in app.caption)
        assert any(item.value == 'Alex lives in Paris.' for item in app.text)
        assert any('替代' in item.value for item in app.markdown)
        assert not any(button.label == '查看完整原文' for button in app.button)
        assert any(text.value == 'I live in Paris.' for text in app.text)
        assert all(method == 'GET' for method, _ in calls)


def test_trace_stages_and_answer_citations_open_delivered_source(settings, sample, monkeypatch):
    model = DeepSeekModel(settings, api_key='synthetic-inspector', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        trace = client.post('/queries', json={'dataset_id': dataset_id, 'sample_id': 'conv-a',
                            'build_id': build_id, 'question': 'Where does Alex live?'}).json()
        build = client.get(f'/builds/{build_id}').json()
        app, calls = inspector_app(client, build, monkeypatch, trace)
        app.run()
        assert not app.exception
        for stage in ('initial', 'expanded', 'effective/delivered', 'answer/citations'):
            app.radio(key=f"trace_stage_{trace['trace_id']}").set_value(stage).run()
            assert not app.exception
            fields = next(item for item in app.expander if item.label == '本阶段已记录字段')
            assert not fields.proto.expanded
        assert not any(button.label == '查看完整原文' for button in app.button)
        assert any(text.value == 'I moved from Paris to Rome on 2 May 2023.' for text in app.text)
        assert any('exact wire：未记录' in item.value for item in app.caption)
        assert all(method == 'GET' for method, _ in calls)


def paged_list_app(monkeypatch, total=45):
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.evidence_ui import page_items
def request(method, path, params):
    values = list(range(st.session_state['total']))
    return {'items': values[params['offset']:params['offset'] + params['limit']], 'total': len(values)}
st.text(','.join(map(str, page_items(request, '/memories', 'memory_page', label='记忆'))))
''', default_timeout=20)
    app.session_state['total'] = total
    return app.run()


def test_pagination_has_visible_ranges_boundaries_and_page_jump(monkeypatch):
    app = paged_list_app(monkeypatch)
    assert not app.exception
    assert app.text[0].value == '第 1 / 3 页'
    assert app.text[-1].value == ','.join(map(str, range(20)))
    assert app.button(key='memory_page_previous').disabled
    app.button(key='memory_page_next').click().run()
    assert app.text[-1].value == ','.join(map(str, range(20, 40)))
    assert any('记忆 21–40 / 共 45 条' in item.value for item in app.caption)
    app.button(key='memory_page_next').click().run()
    assert app.text[-1].value == '40,41,42,43,44'
    assert app.button(key='memory_page_next').disabled
    app.number_input(key='memory_page_page').set_value(1).run()
    assert not app.exception
    assert app.text[-1].value == ','.join(map(str, range(20)))
    assert app.button(key='memory_page_previous').disabled


def test_pagination_recovers_after_records_shrink_and_explains_single_page(monkeypatch):
    app = paged_list_app(monkeypatch)
    app.number_input(key='memory_page_page').set_value(3).run()
    app.session_state['total'] = 6
    app.run()
    assert not app.exception
    assert app.session_state['memory_page'] == 0
    assert app.text[-1].value == '0,1,2,3,4,5'
    assert not app.number_input and not app.button
    assert any('共 6 条记忆 · 已全部显示' == item.value for item in app.caption)
    app.session_state['total'] = 0
    app.run()
    assert not app.exception
    assert any(item.value == '暂无记忆' for item in app.caption)


def test_memory_page_change_selects_a_record_on_that_page(monkeypatch):
    from pathlib import Path
    from locomo_memory.console_replay import ReplayStore

    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    store = ReplayStore(Path(__file__).resolve().parents[1] / 'demo_fixture/product-v1')
    build = store.data['builds'][0]
    build_id = build['build_id']
    seed = store.data['memories'][build_id][0]
    store.data['memories'][build_id] = [{**seed, 'memory_id': f'test-memory-{index}',
                                      'content': f'Synthetic record {index}.'} for index in range(25)]
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.evidence_ui import render_memory_inspector
store = st.session_state['store']
render_memory_inspector(store.request, store.data['builds'][0])
''', default_timeout=20)
    app.session_state['store'] = store
    app.run()
    assert not app.exception
    assert app.radio(key=f'console_memory_{build_id}').value == 'test-memory-0'
    app.button(key=f'console_memory_offset_{build_id}_next').click().run()
    assert not app.exception
    assert app.radio(key=f'console_memory_{build_id}').value == 'test-memory-20'
    assert any(item.value == 'Synthetic record 20.' for item in app.text)
    assert not any(item.value == 'Synthetic record 0.' for item in app.text)
    app.button(key=f'console_memory_offset_{build_id}_previous').click().run()
    assert not app.exception
    assert app.radio(key=f'console_memory_{build_id}').value == 'test-memory-0'
