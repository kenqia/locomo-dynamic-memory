"""A/B experiment bookkeeping and source-delivery audit use retained results."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_report():
    spec = importlib.util.spec_from_file_location('coverage_report_test', ROOT / 'experiments/issue-15-evidence-coverage-live/report.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ab_report_separates_groups_preserves_failure_denominator_and_delivery(tmp_path):
    report = load_report()
    plan = json.loads((ROOT / 'experiments/issue-15-evidence-coverage-live/plan.json').read_text())
    (tmp_path / 'plan.json').write_text(json.dumps(plan))
    outcome = {'status': 'completed_with_errors', 'original_build_unchanged': True,
               'snapshot_build_unchanged': True, 'budget_after': {'reserved_total_calls': 1099, 'limit': 1111}}
    (tmp_path / 'outcome.json').write_text(json.dumps(outcome))
    for label, group in plan['experiments'].items():
        items = []
        for index, question in enumerate(group['questions']):
            for strategy in group['strategies']:
                failed = label == 'B' and index == 0 and strategy == 'dynamic_raw_fallback'
                trace = {'answer': {'status': 'insufficient', 'answer': 'No information available.', 'citations': []},
                         'resolution_budgets': {'resolve': {'source_delivery': {'delivered_source_ids': ['source']}}}}
                result = {'trace': trace, 'qa': {'value': 1}, 'mapping': {'source_ids': ['source']},
                          'source_sets': {'expanded': ['source'], 'answer_context': ['source']},
                          'source_coverage': {'answer_context': 1}, 'usage_summary': {'generation_calls': 1}}
                items.append({'sample_index': index, 'strategy': strategy, 'status': 'failed' if failed else 'succeeded',
                              'result': {} if failed else result})
        run = {'run_id': 'synthetic-' + label, 'items': items,
               'summary': {s: {'usage_summary': {}} for s in group['strategies']}}
        (tmp_path / (label + '-run.json')).write_text(json.dumps(run))
    report.render(tmp_path, tmp_path / 'results')
    saved = json.loads((tmp_path / 'results/results.json').read_text())
    assert len(saved['rows']) == 30
    assert saved['summaries']['A']['dynamic']['planned'] == 5
    assert saved['summaries']['B']['dynamic_raw_fallback']['answerable_f1'] == 7 / 8
    assert saved['summaries']['B']['dynamic_raw_fallback']['successful'] == 9
    assert saved['summaries']['B']['hybrid_no_resolution']['official_refusal_matches'] == 2
    assert saved['rows'][0]['first_resolution_reference_coverage'] == 1
    assert saved['paid_calls'] == 90


def test_frozen_b_questions_exclude_a_and_previously_used_questions():
    folder = ROOT / 'experiments/issue-15-evidence-coverage-live'
    plan = json.loads((folder / 'plan.json').read_text())
    audit = json.loads((folder / 'question-usage-audit.json').read_text())
    a = {q['qa_index'] for q in plan['experiments']['A']['questions']}
    b = {q['qa_index'] for q in plan['experiments']['B']['questions']}
    assert len(a) == 5 and len(b) == 10
    assert not a & b
    assert not b & set(audit['used_qa_indices'])
    assert plan['remaining_authorized_calls'] == 102
    assert plan['budget_before']['reserved_total_calls'] == 1009
    assert plan['budget_before']['limit'] == 1111
    assert len(plan['experiments']['A']['strategies']) == len(plan['experiments']['B']['strategies']) == 2
