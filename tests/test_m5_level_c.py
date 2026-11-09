"""Real production query paths with synthetic sources and mock HTTP only."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import sys

import httpx
import pytest
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m5 import level_c as stage
from tools.m5.offline import write
from tools.m5.extraction_recovery import snapshot
from locomo_memory.builds import BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database
from locomo_memory.imports import import_dataset
from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.retrieval import RetrievalService
from locomo_memory.relations import RelationService
from locomo_memory.schemas import ImportRequest
from locomo_memory.versions import VersionsService
from test_queries import query_provider
from test_builds import completion
from test_retrieval import ControlledEmbedder


@pytest.fixture
def proposal(tmp_path, sample, monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-test-key')
    origin = tmp_path/'source.sqlite3'
    settings = Settings(db_path=origin, model_max_tokens=32768)
    database = Database(origin)
    conversations = []
    for conv in stage.DEV:
        item = deepcopy(sample[0])
        item['sample_id'] = conv
        item['conversation']['session_2'][0]['text'] = 'I moved from Paris to Rome on 2 May 2023.'
        conversations.append(item)
    imported = import_dataset(database, ImportRequest(data=conversations, version='synthetic', license='test-only'))
    model = DeepSeekModel(settings, transport=httpx.MockTransport(query_provider))
    builds = BuildService(database, settings, model)
    pins = {}
    for conv in stage.DEV:
        bid = builds.start(imported.dataset_id, conv)['build_id']
        builds.run(bid)
        RetrievalService(builds, settings, ControlledEmbedder(), model).create_index(bid)
        service = RelationService(builds, model)
        service.start(bid)
        service.run(bid)
        VersionsService(builds).publish(bid)
        pins[conv] = bid
    ordinary = [f'{conv}:qa:{i}' for conv in stage.DEV for i in range(20)]
    diagnostic = [f'{conv}:qa:{i}' for conv in stage.DEV for i in range(20,25)]
    selected = ordinary+diagnostic
    sample_path = tmp_path/'sample.json'
    write(sample_path, dict(ordinary=ordinary, diagnostic=diagnostic))
    document = dict(config=settings.snapshot(), pins=pins, input=dict(dataset_id=imported.dataset_id,
        samples=[dict(sample_id=q.split(':qa:')[0], question='Where does Alex live?', answer='HIDDEN_GOLD', category=4, evidence=['HIDDEN_EVIDENCE']) for q in selected],
        question_identities=[dict(question_id=q) for q in selected]))
    document['input']['samples'][-1]['answer'] = None
    with database.connect() as con:
        con.execute('CREATE TABLE evaluation_runs(run_id TEXT PRIMARY KEY,result_json TEXT NOT NULL)')
        con.execute('INSERT INTO evaluation_runs VALUES (?,?)', ('synthetic-run', json.dumps(document)))
    output = tmp_path/'proposal'
    original = snapshot(origin)
    plan = stage.prepare(output, origin, sample_path, 'synthetic-run')
    assert snapshot(origin) == original
    return origin, output, plan


def test_synthetic_full_pipeline_never_delivers_gold_and_freezes_before_scoring(proposal, monkeypatch):
    origin, output, plan = proposal
    assert not (output/'authorization.json').exists()
    assert plan['policy']['max_requests'] == 1500
    assert plan['policy']['max_usd'] == '346.9824000'
    assert plan['proposal_version'] == 'm5-level-c-input-v2'
    prepared_settings = Settings.model_validate_json((output/'settings.json').read_text())
    assert prepared_settings.thinking_enabled is False
    assert prepared_settings.resolution_input_budget == 192000
    assert all(getattr(prepared_settings, field) == 'disabled' for field in stage.THINKING_FIELDS)
    assert plan['settings_changes']['resolution_thinking_effort'] == dict(source='low', prepared='disabled')
    inputs = json.loads((output/'inputs.json').read_text())
    assert all(set(x) == {'question_id','sample_id','question','stratum'} for x in inputs)
    with sqlite3.connect(output/'memory.sqlite3') as con:
        assert con.execute('SELECT COUNT(*) FROM build_versions').fetchone()[0] == 4
        assert con.execute('SELECT COUNT(*) FROM source_turns WHERE sample_id NOT IN (?,?,?,?)', stage.DEV).fetchone()[0] == 0
        assert not con.execute("SELECT name FROM sqlite_master WHERE name LIKE 'evaluation_%'").fetchall()
        assert con.execute('SELECT COUNT(*) FROM import_artifacts').fetchone()[0] == 0
    observed = []
    bad_answer_attempts = []
    def provider(request):
        raw = request.content.decode()
        assert 'HIDDEN_GOLD' not in raw and 'HIDDEN_EVIDENCE' not in raw
        body = json.loads(raw)
        assert body['thinking'] == {'type':'disabled'}
        assert 'reasoning_effort' not in body
        payload = json.loads(body['messages'][1]['content'])
        observed.append(payload['operation'] if 'operation' in payload else 'analysis')
        if payload.get('operation') == 'answer' and len(bad_answer_attempts) < 3:
            bad_answer_attempts.append(True)
            return completion(dict(status='sufficient', answer='Bad citation', citations=[dict(memory_id='outside-build', source_ids=['outside-source'])]))
        return query_provider(request)
    with pytest.raises(FileNotFoundError):
        stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    assert not observed and not (output/'execution-started.json').exists()
    # Reference database MUST NOT be opened when generation isn't frozen.
    with monkeypatch.context() as patch:
        patch.setattr(stage, 'readonly', lambda path: pytest.fail('premature Gold open'))
        with pytest.raises(FileNotFoundError):
            stage.score(output)
    write(output/'authorization.json', stage.expected_authorization(output))  # Synthetic fixture only.
    before = snapshot(origin)
    freeze = stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    assert snapshot(origin) == before
    assert len(freeze['item_hashes']) == 200
    assert len(observed) == 502
    assert observed.count('resolve') == 100
    with sqlite3.connect(output/'physical-requests.sqlite3') as con:
        assert con.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0] == 502
    with pytest.raises(FileExistsError):
        stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    review = stage.review_units(output)
    assert review == dict(units=200, gold_read=False, reference_status='pending_independent_review')
    units = json.loads((output/'semantic-review-units.json').read_text())['units']
    assert all(u['labels'] is None and len(u['full_conversation_sources']) == 3 for u in units)
    assert 'HIDDEN_GOLD' not in (output/'semantic-review-units.json').read_text()
    scored = stage.score(output)
    assert len(scored['items']) == 200
    assert all(x['qa']['value'] == 0 for x in scored['items'] if x['qa']['value'] is not None)
    assert sum(x['qa']['value'] is None for x in scored['items']) == 2
    assert scored['summary']['ordinary/hybrid_no_resolution']['succeeded'] == 79
    assert scored['summary']['ordinary/hybrid_no_resolution']['scorable'] == 80
    assert scored['summary']['ordinary/dynamic']['planned'] == 80
    assert scored['summary']['diagnostic/dynamic']['planned'] == 20
    # Editing one generation result must be rejected before reference access.
    item_path = output/next(iter(freeze['item_hashes']))
    item_path.write_text('{}')
    with monkeypatch.context() as patch:
        patch.setattr(stage, 'readonly', lambda path: pytest.fail('Gold opened after result mutation'))
        with pytest.raises(ValueError, match='generation_item_changed'):
            stage.score(output)


def test_policy_sample_and_prep_integrity_reject_before_transport(proposal):
    _, output, _ = proposal
    calls = []
    write(output/'authorization.json', stage.expected_authorization(output))
    with sqlite3.connect(output/'memory.sqlite3') as con:
        con.execute("UPDATE build_versions SET status='failed'")
    with pytest.raises(ValueError, match='level_c_prepared_state_changed'):
        stage.execute(output, httpx.MockTransport(lambda req: calls.append(req)), ControlledEmbedder())
    assert calls == [] and not (output/'execution-started.json').exists()
    with pytest.raises(ValueError, match='fixed_sample_size_or_overlap'):
        stage.identities(dict(ordinary=['conv-26:qa:0']*80, diagnostic=['conv-30:qa:0']*20))
    with pytest.raises(ValueError, match='query_settings_outside_proposal'):
        stage.policy_for(100, Settings(model_max_tokens=8192))


def test_frozen_incomplete_manifest_rejects_before_gold(proposal, monkeypatch):
    _, output, _ = proposal
    write(output/'generation-freeze.json', dict(status='generation_complete',
        plan_sha256=stage.sha(output/'plan.json'), item_hashes={}, planned_items=200))
    monkeypatch.setattr(stage, 'readonly', lambda path: pytest.fail('premature Gold open'))
    with pytest.raises(ValueError, match='generation_not_completely_frozen'):
        stage.score(output)


def test_committed_wal_gold_change_is_rejected_before_reference_query(proposal, monkeypatch):
    origin, output, plan = proposal
    # These are explicitly synthetic result fixtures, not provider quality evidence.
    inputs = json.loads((output/'inputs.json').read_text())
    hashes = {}
    for index, question in enumerate(inputs):
        for arm in stage.ARMS:
            item = dict(question_id=question['question_id'], sample_id=question['sample_id'],
                stratum=question['stratum'], arm=arm, outcome='succeeded', prediction='MUTATED_SYNTHETIC_GOLD')
            name = f'items/{index:03d}-{arm}.json'
            write(output/name, item)
            hashes[name] = stage.sha(output/name)
    write(output/'generation-freeze.json', dict(status='generation_complete',
        plan_sha256=stage.sha(output/'plan.json'), item_hashes=hashes, planned_items=200))
    with sqlite3.connect(origin) as writer:
        writer.execute('PRAGMA wal_autocheckpoint=0')
        writer.execute("UPDATE evaluation_runs SET result_json=json_set(result_json,'$.input.samples[0].answer','MUTATED_SYNTHETIC_GOLD')")
        writer.commit()
        # Holding the writer open retains committed content in the WAL.
        assert stage.sha(origin) == plan['source_sha256']
        assert stage.source_storage_identity(origin) != plan['source_storage_identity']
        monkeypatch.setattr(stage, 'readonly', lambda path: pytest.fail('changed Gold queried'))
        with pytest.raises(ValueError, match='reference_source_changed'):
            stage.score(output)
        assert not (output/'scores.json').exists()


def test_preparation_rejects_source_wal_write_during_question_projection(proposal, monkeypatch):
    origin, output, _ = proposal
    original_copy = stage.copy_development
    with sqlite3.connect(origin) as writer:
        writer.execute('PRAGMA wal_autocheckpoint=0')
        def racing_copy(*args):
            original_copy(*args)
            writer.execute("UPDATE datasets SET version='concurrent-synthetic-change'")
            writer.commit()
        monkeypatch.setattr(stage, 'copy_development', racing_copy)
        new_output = output.parent/'racing-proposal'
        with pytest.raises(ValueError, match='source_changed_during_preparation'):
            stage.prepare(new_output, origin, output/'sample.json', 'synthetic-run')
        assert not (new_output/'plan.json').exists()


@pytest.mark.parametrize('field', stage.THINKING_FIELDS)
@pytest.mark.parametrize('effort', ['low', 'high'])
def test_v2_policy_rejects_every_enabled_thinking_field(field, effort):
    settings = Settings(model_max_tokens=32768, **stage.V2_SETTINGS)
    with pytest.raises(ValueError, match='query_settings_outside_proposal'):
        stage.policy_for(100, settings.model_copy(update={field:effort}))


def test_v2_all_five_operations_send_disabled_thinking_in_real_http_body(tmp_path):
    class Accepted(BaseModel):
        ok: bool
    observed = []
    def provider(request):
        body = json.loads(request.content)
        assert body['thinking'] == {'type':'disabled'}
        assert 'reasoning_effort' not in body
        assert body['model'] == 'deepseek-flash' and body['max_tokens'] == 32768
        observed.append(body)
        return completion(dict(ok=True))
    settings = Settings(model_max_tokens=32768, **stage.V2_SETTINGS)
    policy = stage.policy_for(100, settings)
    guard = stage.BudgetTransport(tmp_path/'v2.sqlite3', httpx.MockTransport(provider), **policy)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=guard)
    for operation in ['extract', 'relate', 'query_analysis', 'resolve', 'answer']:
        assert model.generate(operation, {'synthetic':True}, Accepted).value.ok is True
    assert len(observed) == 5


def test_v2_exact_byte_output_request_and_amount_caps(tmp_path):
    settings = Settings(model_max_tokens=32768, **stage.V2_SETTINGS)
    policy = stage.policy_for(100, settings)
    observed = []
    def provider(request):
        observed.append(True)
        return httpx.Response(200, json={'usage':{}})
    path = tmp_path/'v2.sqlite3'
    guard = stage.BudgetTransport(path, httpx.MockTransport(provider), **policy)
    overhead = len(json.dumps([dict(role='user',content='')], ensure_ascii=False).encode())
    messages = [dict(role='user',content='x'*(640000-overhead))]
    assert len(json.dumps(messages,ensure_ascii=False).encode()) == 640000
    def request(messages=messages, output=32768):
        return httpx.Request('POST','https://api.deepseek.com/chat/completions', json=dict(
            model='deepseek-flash', thinking={'type':'disabled'}, messages=messages, max_tokens=output))
    with pytest.raises(ModelFailure,match='physical_request_policy_rejected'):
        guard.handle_request(request([dict(role='user',content=messages[0]['content']+'x')]))
    with pytest.raises(ModelFailure,match='physical_request_policy_rejected'):
        guard.handle_request(request(output=32769))
    assert not observed
    per_request = Decimal('.2313216')
    assert per_request*1500 == Decimal(policy['max_usd']) == Decimal('346.9824')
    # Fill prior reservations without sending 1,499 mock requests. Unknowns retain
    # their full amount; the next exact-boundary request uses the final slot.
    with sqlite3.connect(path) as db:
        db.executemany('INSERT INTO physical_requests VALUES (?,?,?,?)',[
            (str(i),str(per_request),'transport_unknown','null') for i in range(1499)])
    guard.handle_request(request())
    with pytest.raises(ModelFailure,match='physical_request_budget_exhausted'):
        guard.handle_request(request())
    assert len(observed) == 1
    with sqlite3.connect(path) as db:
        assert sum(Decimal(r[0]) for r in db.execute('SELECT reserved_usd FROM physical_requests')) == Decimal('346.9824')
    # Independently prove the amount guard rejects before exhausting request count.
    amount_path = tmp_path/'amount.sqlite3'
    amount_guard = stage.BudgetTransport(amount_path,httpx.MockTransport(provider),**policy)
    with sqlite3.connect(amount_path) as db:
        db.execute('INSERT INTO physical_requests VALUES (?,?,?,?)',('prior','346.9823999','transport_unknown','null'))
    with pytest.raises(ModelFailure,match='physical_request_budget_exhausted'):
        amount_guard.handle_request(request())
    assert len(observed) == 1


@pytest.mark.parametrize('mutation', ['v1_authorization', 'old_plan_sha', 'v1_scope', 'v1_ledger'])
def test_v2_rejects_old_authorization_identity_and_ledger_before_http(proposal, mutation):
    _, output, plan = proposal
    calls = []
    authorization = stage.expected_authorization(output)
    if mutation == 'v1_authorization':
        authorization.pop('proposal_version')
        authorization['scope'] = 'fixed M5 development 80 ordinary + 20 diagnostic questions; Hybrid and Dynamic only; no holdout or Bonus'
        authorization['policy'] = {**plan['policy'],'max_input_bytes':160000,'max_usd':'130.9824000'}
    elif mutation == 'old_plan_sha':
        authorization['plan_sha256'] = 'e7caed32203c567f5fb3ee7fb3a10250400a6da9a9ad453dbfb101eb4f03cf76'
    elif mutation == 'v1_scope':
        plan.pop('proposal_version')
        (output/'plan.json').write_text(json.dumps(plan))
        authorization = stage.expected_authorization(output)
    else:
        with sqlite3.connect(output/'physical-requests.sqlite3') as db:
            old_policy = json.loads(db.execute('SELECT json FROM policy').fetchone()[0])
            old_policy.update(max_input_bytes=160000,max_usd='130.9824000')
            db.execute('UPDATE policy SET json=?',(json.dumps(old_policy,sort_keys=True),))
        with pytest.raises(ValueError,match='budget_policy_changed'):
            stage.BudgetTransport(output/'physical-requests.sqlite3',None,**plan['policy'])
    write(output/'authorization.json', authorization)  # Synthetic fixture only.
    with pytest.raises(ValueError,match='level_c_authorization_mismatch|level_c_plan_changed|level_c_prepared_state_changed'):
        stage.execute(output,httpx.MockTransport(lambda request:calls.append(True)),ControlledEmbedder())
    assert not calls and not (output/'execution-started.json').exists()
