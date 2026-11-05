"""Synthetic complete Builds and mock HTTP; no real held-out artifacts are read."""
from contextlib import contextmanager
from copy import deepcopy
import json
import sqlite3

import httpx
import pytest

from locomo_memory.config import Settings
from locomo_memory.database import Database
from locomo_memory.imports import import_dataset
from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.relations import RelationService
from locomo_memory.schemas import ImportRequest
from tools.m5 import level_e as stage
from tools.m5.offline import DEV, HOLDOUT, sha, write
from test_builds import completion
from test_queries import query_provider
from test_retrieval import ControlledEmbedder


@pytest.fixture
def final_lock(tmp_path, sample, monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'synthetic-key')
    settings = Settings(model_max_tokens=32768, resolution_input_budget=192000,
                        **{field: 'disabled' for field in stage.EFFORTS})
    exports, sources, annotations = {}, {}, []
    for conv in (*DEV, *HOLDOUT):
        item = deepcopy(sample[0])
        item['sample_id'] = conv
        item['conversation']['session_2'][0]['text'] = 'I moved from Paris to Rome on 2 May 2023.'
        item['qa'] = [dict(question='Where does Alex live?', answer='GOLD_SENTINEL',
                           evidence=['EVIDENCE_SENTINEL'], category=4),
                      dict(question='Where does Alex live?', answer=None, evidence=[], category=4)]
        annotations.append(item)
        conversation = {k: item[k] for k in ('sample_id', 'conversation')}
        path = tmp_path/(conv+'.sqlite3')
        local = settings.model_copy(update={'db_path': path})
        imported = import_dataset(Database(path), ImportRequest(data=[conversation], version='synthetic', license='test'))
        model = DeepSeekModel(local, transport=httpx.MockTransport(query_provider))
        q = stage.services(path, local, model, ControlledEmbedder())
        builds = q.versions.builds
        bid = builds.start(imported.dataset_id, conv)['build_id']
        builds.run(bid)
        q.retrieval.create_index(bid)
        relations = RelationService(builds, model)
        relations.start(bid)
        relations.run(bid)
        q.versions.publish(bid)
        bundle = stage.ExportService(q.versions).export(bid)
        export = tmp_path/(conv+'-export.json')
        write(export, bundle.model_dump(mode='json'))
        exports[conv] = dict(path=str(export), sha256=sha(export), build_id=bid, dataset_id=imported.dataset_id)
        if conv in HOLDOUT:
            sources[conv] = dict(path=str(path), storage_identity=stage.source_storage_identity(path))
    reference = tmp_path/'reference.sqlite3'
    imported = import_dataset(Database(reference), ImportRequest(data=annotations, version='reference', license='test'))
    lock = dict(version=stage.VERSION, status='locked', scope=stage.SCOPE, arms=list(stage.ARMS),
                bonus_enabled=False, question_selection='all_original_ordinals', settings=settings.snapshot(),
                implementation_commit='a'*40, implementation_sha256=stage.implementation_hashes(),
                exports=exports, build_sources=sources,
                reference=dict(path=str(reference), dataset_id=imported.dataset_id, artifact_sha256=imported.artifact_sha256,
                    storage_identity=stage.source_storage_identity(reference), questions={conv:dict(count=2,
                        identity_sha256=stage.digest([f'{conv}:qa:{i}' for i in range(2)])) for conv in HOLDOUT}))
    path = tmp_path/'final-system-lock.json'
    write(path, lock)
    return path, lock


def authorized_prepare(tmp_path, final_lock):
    path, lock = final_lock
    output = tmp_path/'level-e'
    plan = stage.prepare(output, path)
    write(output/'authorization.json', stage.expected_authorization(output))
    return output, plan, lock


def test_full_synthetic_pipeline_is_question_only_one_shot_and_freeze_first(tmp_path, final_lock, monkeypatch):
    path, lock = final_lock
    statements = []
    real_readonly = stage.frozen_readonly
    @contextmanager
    def watched(source, identity):
        with real_readonly(source, identity) as con:
            if source == type(path)(lock['reference']['path']):
                con.set_trace_callback(statements.append)
            yield con
    monkeypatch.setattr(stage, 'frozen_readonly', watched)
    output, plan, _ = authorized_prepare(tmp_path, final_lock)
    assert plan['questions'] == 4 and plan['planned_items'] == 8
    assert plan['policy']['max_requests'] == 60
    assert float(plan['policy']['max_usd']) == pytest.approx(3.469824*4)
    assert not any("'$.answer'" in sql or "'$.evidence'" in sql or "'$.category'" in sql for sql in statements)
    assert all('GOLD_SENTINEL' not in p.read_text() and 'EVIDENCE_SENTINEL' not in p.read_text()
               for p in output.glob('*.json'))
    for conv in HOLDOUT:
        with sqlite3.connect(output/(conv+'.sqlite3')) as con:
            assert con.execute('SELECT COUNT(*) FROM import_artifacts WHERE annotations_json LIKE ?', ('%GOLD_SENTINEL%',)).fetchone()[0] == 0
    with monkeypatch.context() as patch:
        patch.setattr(stage, 'source_storage_identity', lambda p: pytest.fail('Gold accessed before freeze'))
        with pytest.raises(FileNotFoundError):
            stage.score(output)
    observed = []
    def provider(request):
        wire = request.content.decode()
        assert 'GOLD_SENTINEL' not in wire and 'EVIDENCE_SENTINEL' not in wire
        body = json.loads(wire)
        assert body['thinking'] == {'type': 'disabled'} and 'reasoning_effort' not in body
        observed.append(body)
        return query_provider(request)
    freeze = stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    assert freeze['planned_items'] == len(freeze['item_hashes']) == 8
    assert freeze['cost']['physical_requests'] == len(observed) == 20
    with pytest.raises(ValueError, match='already_started'):
        stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    before_score = len(statements)
    result = stage.score(output)
    assert any("'$.answer'" in sql for sql in statements[before_score:])
    for arm in stage.ARMS:
        assert result['summary'][arm]['planned'] == 4
        assert result['summary'][arm]['scorable'] == result['summary'][arm]['not_scorable'] == 2
        assert result['category_metrics']['factual_f1']['summary'][arm] == result['summary'][arm]
        assert result['category_metrics']['adversarial_literal_refusal']['summary'][arm]['planned'] == 0
    comparisons = [result['paired_dynamic_minus_hybrid'], *result['per_conversation'].values(),
                   *result['per_category'].values()]
    for comparison in comparisons:
        assert 'four exposed' not in comparison['scope']
        assert 'paired question bootstrap' in comparison['scope']
        assert 'two held-out conversations (conv-43/44)' in comparison['scope']
        assert 'does not support conversation-level generalization' in comparison['scope']
    assert 'not factual correctness' in result['summary_composition']
    assert 'GOLD_SENTINEL' not in (output/'scores.json').read_text()


@pytest.mark.parametrize('mutation', ['unlocked', 'five_exports', 'thinking', 'ids', 'producer',
                                     'commit_missing', 'commit_short', 'commit_nonhex', 'commit_type'])
def test_lock_rejects_before_reference_access(tmp_path, final_lock, monkeypatch, mutation):
    path, lock = final_lock
    if mutation == 'unlocked':
        lock['status'] = 'pending'
    elif mutation == 'five_exports':
        lock['exports'].pop('conv-44')
    elif mutation == 'thinking':
        lock['settings']['resolution_thinking_effort'] = 'low'
    elif mutation == 'ids':
        lock['reference']['questions']['conv-44']['identity_sha256'] = 'wrong'
    elif mutation == 'commit_missing':
        lock.pop('implementation_commit')
    elif mutation.startswith('commit_'):
        lock['implementation_commit'] = {'commit_short': 'a'*39, 'commit_nonhex': 'z'*40,
                                          'commit_type': 123}[mutation]
    else:
        lock['implementation_sha256'] = {}
    path.write_text(json.dumps(lock))
    monkeypatch.setattr(stage, 'readonly', lambda p: pytest.fail('Database opened with invalid final lock'))
    monkeypatch.setattr(stage, 'source_storage_identity', lambda p: pytest.fail('Database accessed with invalid final lock'))
    with pytest.raises(ValueError):
        stage.prepare(tmp_path/'invalid', path)


def test_category_five_is_separate_literal_score_with_failed_items_in_denominator(tmp_path, final_lock, monkeypatch):
    path, lock = final_lock
    reference = type(path)(lock['reference']['path'])
    question = 'What unrecorded prize did Alex win?'
    with sqlite3.connect(reference) as con:
        con.execute('''UPDATE import_artifacts SET annotations_json=json_set(annotations_json,
            '$[4].qa[1].category',5,'$[4].qa[1].question',?,
            '$[5].qa[1].category',5,'$[5].qa[1].question',?)''', (question, question))
    lock['reference']['storage_identity'] = stage.source_storage_identity(reference)
    path.write_text(json.dumps(lock))
    statements = []
    real_readonly = stage.frozen_readonly
    @contextmanager
    def watched(source, identity):
        with real_readonly(source, identity) as con:
            if source == reference:
                con.set_trace_callback(statements.append)
            yield con
    monkeypatch.setattr(stage, 'frozen_readonly', watched)
    output, _, _ = authorized_prepare(tmp_path, final_lock)
    with pytest.raises(FileNotFoundError):
        stage.score(output)
    bad = []
    def provider(request):
        wire = request.content.decode()
        assert 'GOLD_SENTINEL' not in wire and 'EVIDENCE_SENTINEL' not in wire
        payload = json.loads(json.loads(wire)['messages'][1]['content'])
        if payload.get('operation') == 'answer' and payload['question'] == question:
            if len(bad) < 3:
                bad.append(True)
                return completion({})
            memory = payload['memories'][0]
            # Exercise the official literal rule only, not semantic correctness.
            return completion(dict(status=payload['status'], answer='No information available.',
                citations=[dict(memory_id=memory['memory_id'], source_ids=memory['source_ids'])]))
        return query_provider(request)
    freeze = stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    assert len(bad) == 3 and freeze['planned_items'] == 8
    assert not any("'$.answer'" in sql or "'$.evidence'" in sql or "'$.category'" in sql for sql in statements)
    result = stage.score(output)
    groups = result['category_metrics']
    factual = groups['factual_f1']
    refusal = groups['adversarial_literal_refusal']
    assert factual['categories'] == [1, 2, 3, 4] and factual['rule'] == 'official_category_f1'
    assert refusal['categories'] == [5] and refusal['rule'] == 'official_adversarial_refusal'
    for arm in stage.ARMS:
        assert factual['summary'][arm]['planned'] == factual['summary'][arm]['scorable'] == 2
        assert factual['summary'][arm]['failure_zero_mean'] == factual['summary'][arm]['successful_only_mean'] == 0
        assert refusal['summary'][arm]['planned'] == refusal['summary'][arm]['scorable'] == 2
        assert refusal['summary'][arm]['not_scorable'] == refusal['summary'][arm]['unknown'] == 0
        assert refusal['summary'][arm]['successful_only_mean'] == 1
    hybrid = refusal['summary']['hybrid_no_resolution']
    assert hybrid['failed'] == hybrid['succeeded'] == hybrid['successful_scorable'] == 1
    assert hybrid['failure_zero_mean'] == .5
    dynamic = refusal['summary']['dynamic']
    assert dynamic['failed'] == 0 and dynamic['succeeded'] == dynamic['successful_scorable'] == 2
    assert dynamic['failure_zero_mean'] == 1
    assert refusal['paired_dynamic_minus_hybrid']['denominator'] == 2
    assert refusal['paired_dynamic_minus_hybrid']['mean'] == .5
    assert factual['paired_dynamic_minus_hybrid']['mean'] == 0


def test_build_and_annotation_boundaries_are_checked_before_question_projection(tmp_path, final_lock, monkeypatch):
    path, lock = final_lock
    source = type(path)(lock['build_sources']['conv-43']['path'])
    with sqlite3.connect(source) as con:
        con.execute("UPDATE import_artifacts SET annotations_json=?", (json.dumps([dict(sample_id='conv-43', qa=[{'answer':'FORBIDDEN'}])]),))
    lock['build_sources']['conv-43']['storage_identity'] = stage.source_storage_identity(source)
    path.write_text(json.dumps(lock))
    monkeypatch.setattr(stage, 'projected_inputs', lambda *a: pytest.fail('Questions projected before clean Build check'))
    with pytest.raises(ValueError, match='annotations_forbidden'):
        stage.prepare(tmp_path/'invalid', path)


def test_auth_build_and_frozen_item_mutations_fail_before_provider_or_gold(tmp_path, final_lock, monkeypatch):
    output, plan, lock = authorized_prepare(tmp_path, final_lock)
    auth = json.loads((output/'authorization.json').read_text())
    auth['scope'] = 'Level C'
    (output/'authorization.json').write_text(json.dumps(auth))
    with pytest.raises(ValueError, match='authorization_mismatch'):
        stage.execute(output, httpx.MockTransport(lambda r: pytest.fail('unauthorized request')), ControlledEmbedder())
    (output/'authorization.json').write_text(json.dumps(stage.expected_authorization(output)))
    stage.execute(output, httpx.MockTransport(query_provider), ControlledEmbedder())
    item = next((output/'items').glob('*.json'))
    item.write_text('{}')
    with monkeypatch.context() as patch:
        real_identity = stage.source_storage_identity
        def guarded_identity(p):
            if p == type(output)(lock['reference']['path']):
                pytest.fail('Gold accessed after result mutation')
            return real_identity(p)
        patch.setattr(stage, 'source_storage_identity', guarded_identity)
        with pytest.raises(ValueError, match='generation_item_changed'):
            stage.score(output)
    with sqlite3.connect(output/'conv-44.sqlite3') as con:
        con.execute("UPDATE build_versions SET status='failed'")
    with pytest.raises(ValueError, match='build_changed'):
        stage.verify_plan(output)


def test_cross_build_trace_and_budget_policy_rejected(final_lock):
    _, lock = final_lock
    with pytest.raises(ValueError, match='trace_scope_changed'):
        stage.check_trace({'expanded': {'candidates': [{'memory': {'build_id': 'foreign'}}]}}, 'conv-43', 'expected')
    settings = Settings.model_validate(lock['settings'])
    with pytest.raises(ValueError, match='settings_not_locked'):
        stage.policy_for(0, settings)
    with pytest.raises(ValueError, match='settings_not_locked'):
        stage.policy_for(4, settings.model_copy(update={'model_retries': 3}))


def test_real_budget_transport_enforces_input_and_request_caps_and_retains_unknown(tmp_path):
    settings = Settings(model_max_tokens=32768, resolution_input_budget=192000,
                        **{field: 'disabled' for field in stage.EFFORTS})
    path = tmp_path/'ledger.sqlite3'
    guard = stage.BudgetTransport(path, httpx.MockTransport(lambda r: httpx.Response(200, json={})),
                                  **stage.policy_for(1, settings))
    def request(text):
        return httpx.Request('POST', 'https://api.deepseek.com/chat/completions', json=dict(
            model='deepseek-flash', max_tokens=32768, messages=[{'role':'user','content':text}]))
    with pytest.raises(ModelFailure, match='physical_request_policy_rejected'):
        guard.handle_request(request('x'*640000))  # JSON overhead also counts.
    assert stage.ledger_summary(path)['physical_requests'] == 0
    for _ in range(15):
        guard.handle_request(request('synthetic'))
    with pytest.raises(ModelFailure, match='physical_request_budget_exhausted'):
        guard.handle_request(request('synthetic'))
    summary = stage.ledger_summary(path)
    assert summary['physical_requests'] == summary['usage_unknown_requests'] == 15
    assert float(summary['reserved_usd']) > 0


def test_unknown_and_failed_items_are_frozen_and_remain_in_the_denominator(tmp_path, final_lock, monkeypatch):
    output, _, _ = authorized_prepare(tmp_path, final_lock)
    real_services = stage.services
    def services_with_unknown(*args, **kwargs):
        q = real_services(*args, **kwargs)
        def unknown(request):
            raise RuntimeError('PRIVATE_EXCEPTION_TEXT_SENTINEL')
        q.query = unknown
        return q
    monkeypatch.setattr(stage, 'services', services_with_unknown)
    bad = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer' and len(bad) < 3:
            bad.append(True)
            return httpx.Response(200, json={'choices':[{'finish_reason':'stop', 'message':{'content':'{}'}}],
                                             'usage':{'prompt_tokens':1,'completion_tokens':1}})
        return query_provider(request)
    freeze = stage.execute(output, httpx.MockTransport(provider), ControlledEmbedder())
    assert len(freeze['item_hashes']) == 8
    result = stage.score(output)
    assert result['summary']['dynamic']['unknown'] == 4
    assert result['summary']['dynamic']['failure_zero_mean'] == 0
    assert result['summary']['hybrid_no_resolution']['failed'] == 1
    assert all('PRIVATE_EXCEPTION_TEXT_SENTINEL' not in p.read_text() for p in (output/'items').glob('*.json'))


def test_stage_authorization_cannot_be_reused_and_reference_change_blocks_gold(tmp_path, final_lock, monkeypatch):
    output, _, lock = authorized_prepare(tmp_path, final_lock)
    other = tmp_path/'other-stage'
    stage.prepare(other, final_lock[0])
    write(other/'authorization.json', json.loads((output/'authorization.json').read_text()))
    with pytest.raises(ValueError, match='authorization_mismatch'):
        stage.execute(other, httpx.MockTransport(lambda r: pytest.fail('transferred authorization')), ControlledEmbedder())
    stage.execute(output, httpx.MockTransport(query_provider), ControlledEmbedder())
    wal = type(output)(lock['reference']['path']+'-wal')
    wal.write_bytes(b'synthetic changed reference storage')
    monkeypatch.setattr(stage, 'frozen_readonly', lambda *a: pytest.fail('Changed Gold source opened'))
    with pytest.raises(ValueError, match='reference_changed'):
        stage.score(output)


@pytest.mark.parametrize('target', ['authorization.json', 'execution-started.json', 'physical-requests.sqlite3'])
def test_execution_receipts_and_final_ledger_are_frozen(tmp_path, final_lock, monkeypatch, target):
    output, _, _ = authorized_prepare(tmp_path, final_lock)
    stage.execute(output, httpx.MockTransport(query_provider), ControlledEmbedder())
    if target.endswith('.sqlite3'):
        with sqlite3.connect(output/target) as con:
            con.execute("UPDATE physical_requests SET reserved_usd='0'")
    else:
        (output/target).write_text('{}')
    monkeypatch.setattr(stage, 'frozen_readonly', lambda *a: pytest.fail('Gold accessed after receipt mutation'))
    with pytest.raises(ValueError, match='execution_receipt_changed'):
        stage.score(output)


def test_interruption_preserves_marker_and_denies_partial_freeze_scoring(tmp_path, final_lock, monkeypatch):
    output, _, _ = authorized_prepare(tmp_path, final_lock)
    real_services = stage.services
    def interrupted_services(*args, **kwargs):
        q = real_services(*args, **kwargs)
        def interrupt(request):
            raise KeyboardInterrupt()
        q.query = interrupt
        return q
    monkeypatch.setattr(stage, 'services', interrupted_services)
    with pytest.raises(KeyboardInterrupt):
        stage.execute(output, httpx.MockTransport(query_provider), ControlledEmbedder())
    assert (output/'execution-started.json').exists() and (output/'execution-aborted.json').exists()
    assert not (output/'generation-freeze.json').exists()
    assert not json.loads((output/'execution-aborted.json').read_text())['automatic_recovery']
    monkeypatch.setattr(stage, 'frozen_readonly', lambda *a: pytest.fail('Gold opened after interrupted execution'))
    with pytest.raises(FileNotFoundError):
        stage.score(output)
    with pytest.raises(ValueError, match='already_started'):
        stage.execute(output, httpx.MockTransport(query_provider), ControlledEmbedder())
