"""Ordered v6 validation gates; paid commands share a durable campaign budget."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import re
import subprocess
import sys

import httpx

from locomo_memory.config import Settings
from locomo_memory.experiment import write_json
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.model import DeepSeekModel, ModelFailure, DiagnosticPersistenceFailure, utc_now, RELATION_PROMPT_VERSION
from locomo_memory.relation_replay import comparison, source_snapshot
from locomo_memory.relation_schemas import RelationBatch
from v6_campaign import Campaign
from evidence import QuoteAuditTransport

SOURCE = Path('/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v5/memory.sqlite3')
PRIOR = SOURCE.parent / 'provider-budget.sqlite3'
BUILD = '23f0459c5b3b47269dc1497cfc066810'


def body_for(settings, payload, context):
    captured = []
    def provider(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={})
    try:
        DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider)).generate(
            'relate', payload, RelationBatch, context=context)
    except ModelFailure:
        pass
    assert len(captured) == 1
    return captured[0]


def initialize(directory):
    if directory.exists():
        raise ValueError('new_campaign_directory_required')
    check = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_http_diagnostics.py',
                            'tests/test_v6_campaign.py', '-q', '--tb=short'],
                           capture_output=True, text=True, check=False)
    passed = re.search(r'(\d+) passed', check.stdout)
    if check.returncode != 0 or passed is None:
        raise ValueError('controlled_gate_failed')
    directory.mkdir(parents=True, exist_ok=False)
    budget = Campaign(directory/'campaign.sqlite3', PRIOR, create=True)
    assert budget.header['previous_calls'] == 313
    state = {'created_at': utc_now(), 'prompt_version': RELATION_PROMPT_VERSION,
             'gate1': {'status': 'passed', 'tests': int(passed.group(1)), 'new_model_calls': 0,
                       'implementation_sha256': implementation_sha256()},
             'source_database': str(SOURCE), 'source_build_id': BUILD,
             'budget': budget.summary()}
    write_json(directory/'gates.json', state)
    print(json.dumps(state), flush=True)


def lengths(directory, *, after_balance=False):
    state_path = directory/'gates.json'
    state = json.loads(state_path.read_text())
    assert state['gate1']['status'] == 'passed'
    assert state['gate1']['implementation_sha256'] == implementation_sha256()
    target = directory/('lengths-after-balance.json' if after_balance else 'lengths.json')
    if target.exists():
        raise ValueError('length_gate_already_started')
    budget = Campaign(Path(state.get('campaign_directory', directory))/'campaign.sqlite3', PRIOR)
    if after_balance:
        prior = json.loads((directory/'lengths.json').read_text())
        assert prior['status'] == 'blocked' and len(prior['attempts']) == 1
        assert prior['attempts'][0]['metadata']['calls'][0]['http_error_category'] == 'insufficient_balance'
        assert budget.summary()['reserved_total_calls'] >= prior['budget']['reserved_total_calls'] == 314
    with source_snapshot(SOURCE) as (db, source_hash):
        original = Settings.model_validate(json.loads(db.execute(
            'SELECT config_json FROM build_versions WHERE build_id=?', (BUILD,)).fetchone()[0]))
        inputs = [comparison(db, BUILD, ordinal) for ordinal in (73, 91)]
    settings_by_cap = {cap: original.model_copy(update={'model_max_tokens': cap, 'model_retries': 0})
                       for cap in (4096, 8192)}
    # Capture only synthetic requests, then check the exact intended treatment.
    for identity, payload, context in inputs:
        a, b = [body_for(settings_by_cap[cap], payload, context) for cap in (4096, 8192)]
        assert a.pop('max_tokens') == 4096 and b.pop('max_tokens') == 8192
        assert a == b
    report = {'started_at': utc_now(), 'implementation_sha256': implementation_sha256(),
              'source_sha256': source_hash, 'only_treatment': 'max_tokens: 4096 versus 8192',
              'model_retries': 0, 'status': 'running', 'attempts': []}
    write_json(target, report)
    try:
        for cap in (4096, 8192):
            for identity, payload, context in inputs:
                model = DeepSeekModel(settings_by_cap[cap])
                budget.bind(model, 'gate2-lengths', source_task_id=identity['task_id'])
                record = {'source_task_id': identity['task_id'], 'max_tokens': cap,
                          'payload_sha256': identity['payload_sha256'], 'candidate_count': len(context['history'])}
                try:
                    result = model.generate('relate', payload, RelationBatch, context=context)
                    record.update(status='succeeded', covered_candidate_count=len(result.value.judgments),
                                  label_counts=dict(Counter(j.label for j in result.value.judgments)),
                                  judgments=result.value.model_dump(mode='json')['judgments'], metadata=result.metadata)
                except ModelFailure as error:
                    record.update(status=error.code, metadata=error.metadata)
                except DiagnosticPersistenceFailure:
                    # The budget checkpoint survives a fail-closed observer. Preserve
                    # its provider classification without inventing model output.
                    with sqlite3.connect(budget.path.as_uri() + '?mode=ro', uri=True) as db:
                        last = json.loads(db.execute('SELECT metadata FROM calls ORDER BY sequence DESC LIMIT 1').fetchone()[0])
                    record.update(status='stopped', metadata={'calls': [last]},
                                  evidence_source='campaign_ledger_after_observer_stop')
                    report['attempts'].append(record)
                    write_json(target, report)
                    raise
                report['attempts'].append(record)
                write_json(target, report)
        treated = [a for a in report['attempts'] if a['max_tokens'] == 8192]
        success = len(treated) == 2 and all(a['status'] == 'succeeded' and
            a['covered_candidate_count'] == a['candidate_count'] == 20 for a in treated)
        report['status'] = 'passed' if success else 'failed'
    except Exception:
        report.update(status='blocked', error_code='length_gate_requires_review')
    finally:
        report['finished_at'] = utc_now()
        report['budget'] = budget.summary()
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
        write_json(target, report)
        state['gate2'] = {key: report[key] for key in ('status', 'implementation_sha256', 'budget')}
        state['gate2']['report'] = target.name
        write_json(state_path, state)
    print(json.dumps({key: value for key, value in report.items() if key != 'attempts'}), flush=True)
    print(json.dumps({'attempts': [{k: a.get(k) for k in ('source_task_id', 'max_tokens', 'status', 'covered_candidate_count', 'label_counts')}
                                   for a in report['attempts']]}), flush=True)
    return report['status']


def evidence(directory):
    state_path = directory/'gates.json'
    state = json.loads(state_path.read_text())
    assert state['gate2']['status'] == 'passed'
    assert state['gate2']['implementation_sha256'] == implementation_sha256()
    lengths_report = json.loads((directory/state['gate2'].get('report', 'lengths-after-balance.json')).read_text())
    assert all(a['status'] == 'succeeded' for a in lengths_report['attempts'] if a['max_tokens'] == 8192)
    state['gate3'] = {'status': 'not_required', 'reason': 'no_truncation_at_8192_in_fixed_pair'}
    target = directory/'evidence.json'
    if target.exists():
        raise ValueError('evidence_gate_already_started')
    budget = Campaign(Path(state.get('campaign_directory', directory))/'campaign.sqlite3', PRIOR)
    with source_snapshot(SOURCE) as (db, source_hash):
        original = Settings.model_validate(json.loads(db.execute(
            'SELECT config_json FROM build_versions WHERE build_id=?', (BUILD,)).fetchone()[0]))
        inputs = [comparison(db, BUILD, ordinal) for ordinal in (148, 172)]
    settings = original.model_copy(update={'model_max_tokens': 8192, 'model_retries': 0})
    report = {'started_at': utc_now(), 'implementation_sha256': implementation_sha256(),
              'source_sha256': source_hash, 'max_tokens': 8192, 'model_retries': 0,
              'status': 'running', 'attempts': []}
    write_json(target, report)
    try:
        for identity, payload, context in inputs:
            transport = QuoteAuditTransport(context)
            model = DeepSeekModel(settings, transport=transport)
            budget.bind(model, 'gate4-evidence', source_task_id=identity['task_id'])
            record = {'source_task_id': identity['task_id'], 'payload_sha256': identity['payload_sha256'],
                      'candidate_count': len(context['history'])}
            try:
                result = model.generate('relate', payload, RelationBatch, context=context)
                record.update(status='succeeded', covered_candidate_count=len(result.value.judgments),
                              judgments=result.value.model_dump(mode='json')['judgments'], metadata=result.metadata,
                              label_counts=dict(Counter(j.label for j in result.value.judgments)))
            except ModelFailure as error:
                record.update(status=error.code, metadata=error.metadata)
            record['quote_audit'] = transport.observations
            report['attempts'].append(record)
            write_json(target, report)
        complete = all(a['status'] == 'succeeded' and a['covered_candidate_count'] == 20 for a in report['attempts'])
        determined = [o for a in report['attempts'] for o in a['quote_audit'] if o.get('label') not in (None, 'undetermined')]
        report['determined_quotes_exercised'] = len(determined)
        report['status'] = 'passed' if complete and determined and all(o['exact_in_cited_source'] for o in determined) else 'inconclusive' if complete else 'failed'
    except Exception:
        report.update(status='blocked', error_code='evidence_gate_requires_review')
    finally:
        report['finished_at'] = utc_now()
        report['budget'] = budget.summary()
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
        write_json(target, report)
        state['gate4'] = {key: report[key] for key in ('status', 'implementation_sha256', 'budget')}
        write_json(state_path, state)
    print(json.dumps({k: v for k, v in report.items() if k != 'attempts'}), flush=True)
    print(json.dumps({'attempts': [{k: a.get(k) for k in ('source_task_id', 'status', 'label_counts', 'quote_audit')}
                                   for a in report['attempts']]}), flush=True)
    return report['status']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'lengths', 'lengths-after-balance', 'evidence'])
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    try:
        outcome = {'init': initialize, 'lengths': lengths,
                   'lengths-after-balance': lambda path: lengths(path, after_balance=True),
                   'evidence': evidence}[args.command](args.directory.resolve())
        if outcome in {'blocked', 'failed', 'inconclusive'}:
            raise SystemExit(2)
    except Exception:
        print(json.dumps({'status': 'blocked', 'error_code': 'gate_prerequisite_failed'}), flush=True)
        raise SystemExit(2)
