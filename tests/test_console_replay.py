"""Replay must work with sockets and database access forbidden."""
import json
from pathlib import Path
import shutil
import sqlite3
import sys

import httpx
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'demo_fixture/product-v1'


def test_replay_serves_frozen_builds_sources_and_actual_failures_without_io(monkeypatch):
    from locomo_memory.console_replay import ReplayStore
    monkeypatch.setattr(httpx, 'request', lambda *a, **kw: pytest.fail('Replay made a network request'))
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: pytest.fail('Replay opened a database'))
    store = ReplayStore(FIXTURE)
    dataset = store.request('GET', '/datasets')['items'][0]
    builds = store.request('GET', '/builds', params={'dataset_id': dataset['dataset_id']})['items']
    assert len(builds) == 2 and builds[0]['build_id'] != builds[1]['build_id']
    kinds = {case['case_id']: case for case in store.cases}
    for kind in ('success', 'insufficient', 'citation_anomaly', 'budget_failure'):
        case = kinds[kind]
        trace = store.request('GET', '/queries/' + case['trace_id'])
        assert trace['outcome'] == case['outcome']
    assert store.request('GET', '/queries/' + kinds['budget_failure']['trace_id'])['error']['code'] == 'conflict_evidence_budget_exceeded'
    assert store.request('GET', '/queries/' + kinds['success']['trace_id'])['answer']['answer'] == 'Alex lives in Rome.'
    assert store.request('GET', '/queries/' + kinds['historical']['trace_id'])['answer']['answer'] == 'Alex lives in Paris.'
    assert store.request('GET', '/queries/' + kinds['budget_failure']['trace_id'])['diagnostics']['answer'] == []
    source = store.request('GET', f"/datasets/{dataset['dataset_id']}/conversations/conv-a/turns/D1:1")
    assert source['text'] == 'I live in Paris.'
    with pytest.raises(ValueError, match='read_only'):
        store.request('POST', '/queries')
    with pytest.raises(httpx.HTTPStatusError):
        store.request('GET', '/datasets/other/conversations/conv-a/turns/D1:1')


def test_replay_rejects_modified_snapshot_and_contains_no_runtime_database_or_wire(tmp_path):
    from locomo_memory.console_replay import ReplayStore
    shutil.copytree(FIXTURE, tmp_path / 'bundle')
    path = tmp_path / 'bundle/snapshot.json'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='checksum'):
        ReplayStore(tmp_path / 'bundle')
    data = json.loads((FIXTURE / 'snapshot.json').read_text(encoding='utf-8'))

    def inspect(value):
        if isinstance(value, dict):
            assert not set(value) & {'db_path', 'api_key', 'exact_wire', 'request', 'response', 'prompts', 'answer_input'}
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)

    inspect(data)


def test_replay_checksums_survive_windows_checkout_line_endings(tmp_path):
    from locomo_memory.console_replay import ReplayStore
    shutil.copytree(FIXTURE, tmp_path / 'bundle')
    for name in ('snapshot.json', 'research-evidence.json'):
        path = tmp_path / 'bundle' / name
        path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    assert len(ReplayStore(tmp_path / 'bundle').cases) == 6


def test_entire_replay_ui_keeps_plan_negation_unknown_and_failure_visible(monkeypatch):
    from locomo_memory.console_replay import ReplayStore
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    monkeypatch.setattr(httpx, 'request', lambda *a, **kw: pytest.fail('Unexpected HTTP'))
    monkeypatch.setattr(sqlite3, 'connect', lambda *a, **kw: pytest.fail('Unexpected database'))
    store = ReplayStore(FIXTURE)
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.console_ui import render_console
store = st.session_state['store']
render_console(store.request, evidence_path=store.evidence_path, replay_cases=store.cases)
''', default_timeout=20)
    app.session_state['store'] = store
    app.run()
    app.radio(key='console_page').set_value('Memory').run()
    assert not app.exception
    table = app.dataframe[0].value.set_index('content')
    assert table.loc['Alex plans to visit Tokyo.', '陈述性质'] == 'plan'
    assert table.loc['Alex does not own a car.', '极性'] == 'negative'
    assert set(table['事件起始']) == {'unknown'}
    app.radio(key='console_page').set_value('Query/Evidence').run()
    app.selectbox(key='console_replay_case').set_value('budget_failure').run()
    app.button(key='console_load_case').click().run()
    assert not app.exception
    assert any('conflict_evidence_budget_exceeded' in error.value for error in app.error)
    app.selectbox(key='console_replay_case').set_value('citation_anomaly').run()
    app.button(key='console_load_case').click().run()
    assert any('answer / invalid_output' in error.value for error in app.error)


def test_source_inspector_does_not_display_mismatched_source_identity(monkeypatch):
    from locomo_memory.console_replay import ReplayStore
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    store = ReplayStore(FIXTURE)
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.evidence_ui import render_sources
store = st.session_state['store']
build = store.data['builds'][0]
source_id = store.data['sources'][0]['source_id']
def mismatched(method, path, **kwargs):
    result = store.request(method, path, **kwargs)
    return {**result, 'source_id': 'other/conv-a/D1:1', 'text': 'Wrong conversation text'}
render_sources(mismatched, [source_id], build, 'identity_check')
''', default_timeout=20)
    app.session_state['store'] = store
    app.run()
    app.button(key='identity_check_open').click().run()
    assert not app.exception
    assert any('身份与引用不一致' in error.value for error in app.error)
    assert not app.text
