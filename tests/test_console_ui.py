"""Console acceptance at the Streamlit and public HTTP boundaries."""
import sys

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def console_app(client, monkeypatch):
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.console_ui import render_console
render_console(st.session_state['request'])
''', default_timeout=20)
    calls = []

    def request(method, path, **kwargs):
        calls.append((method, path))
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    app.session_state['request'] = request
    return app, calls


def test_overview_keeps_frozen_real_run_separate_from_empty_backend(client, monkeypatch):
    app, calls = console_app(client, monkeypatch)
    app.run()
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics['原 Run 计划组合'] == '3028'
    assert metrics['成功'] == '2969'
    assert metrics['失败'] == '56'
    assert metrics['unknown'] == '3'
    assert any('尚无数据集' in item.value for item in app.info)
    assert any('a2abe1fb49be45ccba291728e1f6b3c9' in item.value for item in app.caption)
    assert all(method == 'GET' for method, _ in calls)


def test_console_navigation_reads_memories_and_saved_trace_without_generation(settings, sample, monkeypatch):
    model = DeepSeekModel(settings, api_key='synthetic-console-only',
                          transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, build_id = complete_build(client, sample)
        response = client.post('/queries', json={'dataset_id': dataset_id, 'sample_id': 'conv-a',
                               'build_id': build_id, 'question': 'Where does Alex live?'})
        assert response.status_code == 201
        trace_id = response.json()['trace_id']
        app, calls = console_app(client, monkeypatch)
        app.run()
        assert not app.exception
        assert app.session_state[f'console_build_{dataset_id}_conv-a'] == build_id
        assert not any(build_id in item.value for item in app.caption)
        app.radio(key='console_page').set_value('Memory').run()
        assert not app.exception
        assert 'Alex lives in Paris.' in app.radio(key=f'console_memory_{build_id}').options
        assert not app.dataframe
        app.radio(key='console_page').set_value('Query/Evidence').run()
        app.text_input(key='console_trace_id').set_value(trace_id).run()
        app.button(key='console_load_trace').click().run()
        assert not app.exception
        assert any(item.value == 'Alex lives in Rome.' for item in app.text)
        app.radio(key='console_role').set_value('评审者').run()
        assert any(item.value == 'Alex lives in Rome.' for item in app.text)
        for page in ('Experiments', 'Demo', 'Overview'):
            app.radio(key='console_page').set_value(page).run()
            assert not app.exception
        assert all(method == 'GET' for method, _ in calls)


@pytest.mark.parametrize('failure', ['connection', 'http', 'contract'])
def test_backend_failure_keeps_frozen_report_visible_without_echoing_input(client, monkeypatch, failure):
    app, _ = console_app(client, monkeypatch)

    def unavailable(method, path, **kwargs):
        if failure == 'contract':
            return {'unexpected': 'private-input'}
        request = httpx.Request(method, 'http://localhost' + path)
        if failure == 'connection':
            raise httpx.ConnectError('private-input', request=request)
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError('private-input', request=request, response=response)

    app.session_state['request'] = unavailable
    app.run()
    assert not app.exception
    assert app.error
    assert all('private-input' not in error.value for error in app.error)
    assert {item.label: item.value for item in app.metric}['unknown'] == '3'


def test_experiments_retains_unmeasured_full_denominator_as_unknown(client, monkeypatch):
    app, _ = console_app(client, monkeypatch)
    app.run()
    app.radio(key='console_page').set_value('Experiments').run()
    assert not app.exception
    metrics = {item.label: item.value for item in app.metric}
    assert metrics['完整分母 QA'] == '0.5151'
    app.radio(key='experiment_group_strategy').set_value('full_text').run()
    assert {item.label: item.value for item in app.metric}['完整分母 QA'] == 'unknown'
    app.radio(key='experiment_group_strategy').set_value('hybrid_no_resolution').run()
    assert {item.label: item.value for item in app.metric}['完整分母 QA'] == 'unknown'


def test_overview_actions_navigate_without_generation(client, monkeypatch):
    app, calls = console_app(client, monkeypatch)
    app.run()
    assert app.button(key='overview_memory').disabled
    assert app.button(key='overview_trace').disabled
    assert not app.button(key='overview_experiments').disabled
    app.button(key='overview_experiments').click().run()
    assert not app.exception
    assert app.radio(key='console_page').value == 'Experiments'
    assert all(method == 'GET' for method, _ in calls)


def test_trace_from_other_build_is_rejected(settings, sample, monkeypatch):
    model = DeepSeekModel(settings, api_key='synthetic-console-only',
                          transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset_id, old_build_id = complete_build(client, sample)
        trace = client.post('/queries', json={'dataset_id': dataset_id, 'sample_id': 'conv-a',
                            'build_id': old_build_id, 'question': 'Where does Alex live?'}).json()
        _, new_build_id = complete_build(client, sample)
        assert old_build_id != new_build_id
        app, calls = console_app(client, monkeypatch)
        app.run()
        app.radio(key='console_page').set_value('Query/Evidence').run()
        app.text_input(key='console_trace_id').set_value(trace['trace_id']).run()
        app.button(key='console_load_trace').click().run()
        assert not app.exception
        assert any('属于其他 Build' in warning.value for warning in app.warning)
        assert not app.chat_message
        assert not any(item.value == 'Alex lives in Rome.' for item in app.text)
        assert all(method == 'GET' for method, _ in calls)


def test_overview_uses_recorded_completion_time_for_recent_report(client, monkeypatch):
    app, calls = console_app(client, monkeypatch)
    backend = app.session_state['request']
    timestamps = {'a-old': '2026-11-03T08:00:00Z', 'z-new': '2026-11-04T08:00:00Z', 'm-unknown': None}

    def reports(method, path, **kwargs):
        if path == '/evaluation-runs':
            calls.append((method, path))
            return {'items': [{'run_id': name, 'status': 'completed' if stamp else 'unknown'}
                              for name, stamp in timestamps.items()], 'total': 3, 'limit': 20, 'offset': 0}
        if path.startswith('/evaluation-runs/'):
            calls.append((method, path))
            run_id = path.split('/')[2]
            return {'run_id': run_id, 'completed_at': timestamps[run_id], 'status': 'completed'}
        return backend(method, path, **kwargs)

    app.session_state['request'] = reports
    app.run()
    assert not app.exception
    assert any('本页最近完成报告：z-new' in item.value for item in app.caption)
    assert app.radio(key='console_run').value == 'z-new'
    app.button(key='console_load_report').click().run()
    assert any('2026-11-04T08:00:00Z' in item.value for item in app.caption)
    assert all(method == 'GET' for method, _ in calls)
