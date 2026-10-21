"""Experiment diagnostics must retain neither response text nor untrusted errors."""
import importlib.util
import json
from pathlib import Path
import sqlite3

import httpx

from locomo_memory.query_schemas import EvidenceAnswer


def repeat_module():
    path = Path(__file__).resolve().parents[1] / 'experiments/issue-15-answer-output-live/run.py'
    spec = importlib.util.spec_from_file_location('answer_repeat_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_response_audit_keeps_fixed_reason_and_never_retains_answer(tmp_path, monkeypatch):
    module = repeat_module()
    synthetic_private_text = 'synthetic response body must not be retained'
    response = {'choices': [{'message': {'content': json.dumps({
        'status': 'sufficient', 'answer': synthetic_private_text, 'citations': []})}}]}
    monkeypatch.setattr(httpx, 'HTTPTransport', lambda: httpx.MockTransport(
        lambda request: httpx.Response(200, json=response)))
    audit = module.ValidationAudit(tmp_path)
    audit.schema, audit.context, audit.operation = EvidenceAnswer, {'memories': {}, 'status': 'insufficient'}, 'answer'
    audit.handle_request(httpx.Request('POST', 'https://synthetic.invalid'))
    saved = (tmp_path / 'validation-causes.json').read_text()
    assert synthetic_private_text not in saved
    assert 'reasoning_content' not in saved
    errors = json.loads(saved)[0]['errors']
    assert errors == [{'type': 'value_error', 'field_path': None,
                       'cause': 'Answer must preserve evidence uncertainty'}]


def test_snapshot_digest_detects_mutated_artifact_and_reuses_identical_copy(tmp_path, monkeypatch):
    module = repeat_module()
    monkeypatch.setattr(module, 'IMMUTABLE', ['memories'])
    source, snapshot = tmp_path / 'source.sqlite3', tmp_path / 'snapshot.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE memories(memory_id TEXT, vector BLOB)')
        db.execute('INSERT INTO memories VALUES (?, ?)', ('memory', b'original-vector'))
        with sqlite3.connect(snapshot) as target:
            db.commit()
            db.backup(target)
    before = module.artifact_digest(source)
    assert module.artifact_digest(snapshot) == before
    with sqlite3.connect(snapshot) as db:
        db.execute('UPDATE memories SET vector=?', (b'mutated-vector',))
    assert module.artifact_digest(snapshot) != before
    assert module.artifact_digest(source) == before


def test_repeat_report_keeps_failed_item_in_denominator(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'experiments/issue-15-answer-output-live/report.py'
    spec = importlib.util.spec_from_file_location('answer_repeat_report_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads((path.parents[1] / 'issue-15-thinking-qa/plan.json').read_text())
    original.update(source_build_id='synthetic-build', source_directory='synthetic-source',
                    budget_before={'reserved_total_calls': 911})
    items = []
    for index, _ in enumerate(original['questions']):
        for strategy in original['strategies']:
            failed = index == 0 and strategy == 'dynamic'
            trace = {'answer': {'answer': 'No information available.', 'status': 'insufficient', 'citations': []},
                     'source_delivery': {'expected_source_ids': ['source'], 'delivered_source_ids': ['source'], 'provider_accepted': True},
                     'evidence_budget': {'truncated': False}, 'operations': {'answer': {'calls': [{'http_status': 200}]}}}
            items.append({'sample_index': index, 'strategy': strategy, 'status': 'failed' if failed else 'succeeded',
                          'attempts': [], 'result': {} if failed else {'trace': trace, 'qa': {'value': 1}}})
    documents = {'plan': original,
                 'outcome': {'status': 'completed_with_errors', 'build_id': 'synthetic-build',
                             'snapshot_build_unchanged': True, 'original_build_unchanged': True,
                             'budget_after': {'reserved_total_calls': 1001, 'limit': 1111}},
                 'evaluation-run': {'run_id': 'synthetic-run', 'items': items,
                                    'summary': {s: {'usage_summary': {'reported_tokens': {'total_tokens': 0}}}
                                                for s in original['strategies']}}}
    for name, value in documents.items():
        (tmp_path / (name + '.json')).write_text(json.dumps(value))
    module.render(tmp_path, tmp_path / 'results')
    saved = json.loads((tmp_path / 'results/comparison.json').read_text())
    assert saved['comparison']['dynamic']['after_answerable_f1'] == 7 / 8
    assert saved['comparison']['dynamic']['after_success'] == 9
    assert saved['comparison']['dynamic']['official_refusal_matches'] == 2
    assert saved['new_paid_calls'] == 90
    assert len(saved['rows']) == 40
