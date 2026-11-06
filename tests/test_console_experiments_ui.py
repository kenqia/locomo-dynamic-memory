"""Frozen aggregate comparison keeps dimensions, denominators and unknowns honest."""
from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


def test_frozen_comparison_switches_dimensions_and_separates_missing_repair_runs(monkeypatch):
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    path = Path(__file__).resolve().parents[1] / 'docs/team-v2/research-evidence.json'
    app = AppTest.from_string('''
import json
import streamlit as st
from locomo_memory.frozen_report_ui import render_experiment_comparison
render_experiment_comparison(json.loads(st.session_state['evidence']))
''', default_timeout=20)
    app.session_state['evidence'] = path.read_text(encoding='utf-8')
    app.run()
    assert not app.exception
    assert {m.label: m.value for m in app.metric}['可比成功配对'] == '705'
    table = app.dataframe[0].value.set_index('strategy')
    assert table.loc['full_text', '完整分母 QA'] == 'unknown'
    for dimension in ('conversation', 'category', 'strategy'):
        app.selectbox(key='experiment_dimension').set_value(dimension).run()
        assert not app.exception
    app.radio(key='experiment_run_set').set_value('supplementary').run()
    assert not app.exception
    assert any('未提供' in message.value for message in app.info)
    assert not app.dataframe
