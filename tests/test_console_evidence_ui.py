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
        app.button(key=f'memory_source_{build_id}_open').click().run()
        assert not app.exception
        assert any(text.value == 'I live in Paris.' for text in app.text)
        assert all(method == 'GET' for method, _ in calls)


def test_trace_stages_and_answer_citations_open_delivered_source(settings, sample, monkeypatch):
    model = DeepSeekModel(settings, api_key='synthetic-inspector', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        trace = client.post('/queries', json={'strategy': 'dynamic', 'dataset_id': dataset_id, 'sample_id': 'conv-a',
                            'build_id': build_id, 'question': 'Where does Alex live?'}).json()
        build = client.get(f'/builds/{build_id}').json()
        app, calls = inspector_app(client, build, monkeypatch, trace)
        app.run()
        assert not app.exception
        for stage in ('initial', 'expanded', 'effective/delivered', 'answer/citations'):
            app.radio(key=f"trace_stage_{trace['trace_id']}").set_value(stage).run()
            assert not app.exception
        app.button(key=f"answer_source_{trace['trace_id']}_open").click().run()
        assert not app.exception
        assert any(text.value == 'I moved from Paris to Rome on 2 May 2023.' for text in app.text)
        assert any('exact wire：未记录' in item.value for item in app.caption)
        assert all(method == 'GET' for method, _ in calls)
