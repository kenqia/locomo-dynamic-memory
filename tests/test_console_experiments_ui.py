"""Frozen aggregate comparison keeps dimensions, denominators and unknowns honest."""
from pathlib import Path
import sys
import json

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
    table = app.dataframe[0].value.set_index('分组')
    assert table.loc['Dynamic', '运行成功率'] == '93.66%'
    metrics = {m.label: m.value for m in app.metric}
    assert metrics['本组计划'] == '757' and metrics['本组失败'] == '48'
    assert metrics['已知完成率（含失败）'] == '100.00%'
    assert metrics['完整分母 QA'] == '0.5151'
    details = next(json.loads(item.value) for item in app.json if 'provider_cost_estimates' in item.value)
    assert details['groups']['dynamic']['full_denominator_qa_score'] == 0.5151333813668602
    assert details['groups']['full_text']['full_denominator_qa_score'] is None
    app.selectbox(key='experiment_cost').set_value('dynamic').run()
    assert {m.label: m.value for m in app.metric}['已知峰值价估算 CNY'] == '98.9305'
    for dimension in ('conversation', 'category', 'strategy'):
        app.selectbox(key='experiment_dimension').set_value(dimension).run()
        assert not app.exception
    app.radio(key='experiment_run_set').set_value('supplementary').run()
    assert not app.exception
    assert any('未提供' in message.value for message in app.info)
    assert not app.dataframe


def test_display_precision_retains_unknown_and_small_nonzero_cost():
    from locomo_memory.frozen_report_ui import shown, completion_rate
    assert shown(None) == 'unknown'
    assert shown(0) == '0.0000'
    assert shown(0.00000001) != '0.0000'
    assert shown(0.9365918097754293, percent=True) == '93.66%'
    assert completion_rate({'planned': 3, 'states': {'succeeded': 1, 'failed': 1}}) is None
    assert completion_rate({'planned': 3, 'states': {'succeeded': 1, 'failed': 1, 'unknown': 1}}) == 2 / 3
