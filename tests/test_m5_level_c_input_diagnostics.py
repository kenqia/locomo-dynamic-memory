"""Offline reconstruction tests use synthetic text, never real QA or annotations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from locomo_memory.config import Settings
from locomo_memory.imports import canonical_json
from locomo_memory.model import request_messages, request_token_estimate
from locomo_memory.query_schemas import EffectiveResolution
from locomo_memory.resolution_delivery import complete_resolution_input
from locomo_memory.temporal import query_memory_times
from test_m5_level_c import proposal
from test_queries import query_provider
from test_retrieval import ControlledEmbedder
from tools.m5 import level_c as stage_tool
from tools.m5.offline import write
from tools.m5.level_c_input_diagnostics import (
    DEV, first_resolve_payload, inspect_payload, messages_bytes, readonly, run,
)


def synthetic(connection, conv='conv-26'):
    dataset, build = 'synthetic-dataset', f'synthetic-build-{conv}'
    sources = [dict(source_id=f'{dataset}/{conv}/D1:{i}', dataset_id=dataset,
                    sample_id=conv, session_id='session_1', dia_id=f'D1:{i}', speaker='Alex',
                    session_time='1:00 pm on 8 May, 2023',
                    text='SYNTHETIC_PRIVATE_SOURCE "字"\nI moved yesterday.  Preserve  spaces.', position=i-1)
               for i in (1, 2)]
    connection.executemany('INSERT INTO source_turns VALUES (?,?,?,?,?,?,?,?,?)',
                           [tuple(source.values()) for source in sources])
    memories = [json.loads(canonical_json(dict(memory_id=f'{build}-m{i}', build_id=build,
                  dataset_id=dataset, sample_id=conv, content='SYNTHETIC_PRIVATE_MEMORY',
                  source_ids=[sources[1]['source_id'], sources[0]['source_id']] if i == 1 else [sources[0]['source_id']],
                  time=dict(original_expression='yesterday', anchor_source_id=sources[0]['source_id'],
                            basis='old', event_start=None, event_end=None, valid_from=None, valid_to=None))))
                for i in (1, 2)]
    relation = dict(old_memory_id=memories[0]['memory_id'], new_memory_id=memories[1]['memory_id'],
                    label='RETAIN', reason='SYNTHETIC_PRIVATE_REASON',
                    applicability={'condition':None}, relation_id=f'{build}-r1', build_id=build)
    connection.execute('INSERT INTO memory_relations VALUES (?,?,?)',
                       (build, relation['relation_id'], json.dumps(relation)))
    source_map = {sources[1]['source_id']:sources[1], sources[0]['source_id']:sources[0]}
    normalized, diagnostics = query_memory_times({memory['memory_id']:memory for memory in memories}, source_map)
    analysis = dict(status='succeeded', result=dict(entities=['Alex'], topic='home', time=None, keywords=['move']),
                    error_code=None, model_metadata={'calls':[]}, prompt_version='synthetic')
    timing = dict(requested_date=None, anchor_date='2023-05-08', origin='conversation_cutoff',
                  cutoff='2023-05-08T13:00:00', cutoff_source_time=sources[0]['session_time'], beyond_cutoff=False)
    payload = dict(operation='resolve', question='SYNTHETIC_PRIVATE_QUESTION', time=timing, analysis=analysis,
                   memories=list(normalized.values()), sources=list(source_map.values()),
                   relations=[relation], candidates_truncated=False)
    settings = Settings(model_max_tokens=32768, resolution_input_budget=96000)
    _, audit = complete_resolution_input(payload, settings)
    trace = dict(sample_id=conv, dataset_id=dataset, build_id=build, question=payload['question'],
                 initial=dict(question=payload['question'], analysis=analysis, initial_truncated=False),
                 expanded=dict(question=payload['question'], candidates=[{'memory':memory} for memory in memories], truncated=False),
                 time=timing, time_diagnostics=diagnostics, relations=[relation],
                 resolution_budgets={'resolve':audit}, config=settings.snapshot(), operations={'resolve':{'calls':[{}]}})
    return dict(arm='dynamic', sample_id=conv, outcome='succeeded', trace=trace), payload, settings


def database(path=':memory:'):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE source_turns(source_id TEXT,dataset_id TEXT,sample_id TEXT,session_id TEXT,dia_id TEXT,speaker TEXT,session_time TEXT,text TEXT,position INT)')
    connection.execute('CREATE TABLE memory_relations(build_id TEXT,relation_id TEXT,relation_json TEXT)')
    return connection


def test_canonical_failed_trace_restores_full_original_request_bytes():
    with database() as connection:
        item, original, settings = synthetic(connection)
        # Failure persistence sorts nested keys, including analysis, time and relations.
        persisted = json.loads(canonical_json(item))
        restored = first_resolve_payload(persisted, connection)
        assert messages_bytes(request_messages('resolve', restored, EffectiveResolution)) == messages_bytes(
            request_messages('resolve', original, EffectiveResolution))
        assert len(restored['memories']) == 2 and len(restored['sources']) == 2
        assert restored['sources'][0]['text'] == original['sources'][0]['text']
        assert restored['memories'][0]['time']['event_start'] == '2023-05-07'
        assert inspect_payload(restored, settings)['input_token_estimate'] == item['trace']['resolution_budgets']['resolve']['input_token_count']


@pytest.mark.parametrize('defect,code', [('source','missing_development_source'),
    ('candidate','complete_memory_order_mismatch'), ('relation','relation_snapshot_mismatch')])
def test_missing_or_changed_input_fails_closed_without_text(defect, code):
    with database() as connection:
        item, _, _ = synthetic(connection)
        if defect == 'source':
            connection.execute('DELETE FROM source_turns')
        elif defect == 'candidate':
            item['trace']['resolution_budgets']['resolve']['complete_memory_ids'].reverse()
        else:
            connection.execute('DELETE FROM memory_relations')
        with pytest.raises(ValueError, match=f'^{code}$') as error:
            first_resolve_payload(item, connection)
        assert 'SYNTHETIC_PRIVATE' not in str(error.value)


def test_two_independent_boundary_gates_and_lossless_probe():
    with database() as connection:
        _, payload, settings = synthetic(connection)
        before = deepcopy(payload)
        estimate = request_token_estimate('resolve', payload, EffectiveResolution)
        size = len(messages_bytes(request_messages('resolve', payload, EffectiveResolution)))
        exact = inspect_payload(payload, settings.model_copy(update={'resolution_input_budget':estimate}), size)
        assert exact['within_complete_token_budget'] and exact['within_transport_byte_cap']
        byte_only = inspect_payload(payload, settings.model_copy(update={'resolution_input_budget':estimate}), size-1)
        assert byte_only['within_complete_token_budget'] and not byte_only['within_transport_byte_cap']
        token_only = inspect_payload(payload, settings.model_copy(update={'resolution_input_budget':estimate-1}), size)
        assert not token_only['within_complete_token_budget'] and token_only['within_transport_byte_cap']
        assert exact['compact_user_json_saved_bytes'] > 0
        assert exact['compact_user_json_token_estimate'] == estimate
        assert exact['outer_http_whitespace_saved_policy_bytes'] == 0
        assert payload == before


def test_incomplete_100_dynamic_fixture_without_plan_is_rejected(tmp_path, monkeypatch):
    # Any accidental client/provider construction is an error, rather than a mock response.
    import httpx
    from locomo_memory.model import DeepSeekModel
    def forbidden(*args, **kwargs):
        raise AssertionError('provider_or_network_must_not_run')
    monkeypatch.setattr(httpx, 'Client', forbidden)
    monkeypatch.setattr(DeepSeekModel, 'generate', forbidden)
    stage = tmp_path/'stage'; stage.mkdir()
    with database(stage/'memory.sqlite3') as connection:
        seeds = {conv:synthetic(connection, conv) for conv in DEV}
    inputs, hashes = [], {}
    (stage/'items').mkdir()
    for index in range(100):
        conv, local = DEV[index//25], index%25
        item, _, settings = deepcopy(seeds[conv])
        item.update(question_id=f'{conv}:qa:{local}', stratum='ordinary' if local < 20 else 'diagnostic')
        inputs.append(dict(question_id=item['question_id'], sample_id=conv, stratum=item['stratum'], question=item['trace']['question']))
        name = f'items/{index:03d}-dynamic.json'
        raw = json.dumps(item).encode(); (stage/name).write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    (stage/'settings.json').write_text(json.dumps(settings.snapshot()))
    (stage/'inputs.json').write_text(json.dumps(inputs))
    (stage/'generation-freeze.json').write_text(json.dumps(dict(status='generation_complete', planned_items=200, item_hashes=hashes)))
    before = {path:hashlib.sha256(path.read_bytes()).hexdigest() for path in stage.rglob('*') if path.is_file()}
    with pytest.raises(FileNotFoundError):
        run(stage)
    after = {path:hashlib.sha256(path.read_bytes()).hexdigest() for path in stage.rglob('*') if path.is_file()}
    assert before == after


def test_wire_grouping_counts_guidance_and_cannot_bypass_prior_complete_token_gate():
    from locomo_memory.m5_wire_compression import GUIDANCE, encode_request
    from tools.m5.level_c_input_diagnostics import summarize
    with database() as connection:
        _, payload, settings = synthetic(connection)
        base = payload['memories'][0]
        payload['memories'] = [dict(base, memory_id=f'm{index}',
            entity_id='synthetic-entity-'*15, state_dimension='synthetic_dimension_'*15,
            state_key='synthetic-key-'*15) for index in range(30)]
        before = deepcopy(payload)
        estimate = request_token_estimate('resolve', payload, EffectiveResolution)
        measured = inspect_payload(payload, settings.model_copy(update={'resolution_input_budget':estimate-1}))
        grouped = measured['wire_grouping']
        assert grouped['applied'] and grouped['roundtrip_input_wire_payload']
        original_messages = request_messages('resolve', payload, EffectiveResolution)
        encoded, _ = encode_request({'messages':original_messages})
        assert encoded['messages'][0]['content'].endswith(GUIDANCE)
        assert grouped['messages_utf8_bytes'] == len(messages_bytes(encoded['messages']))
        assert grouped['input_token_estimate'] < estimate
        assert not measured['within_complete_token_budget']
        row = dict(measured, outcome='failed', observed_error_code='complete_resolution_input_budget_exceeded',
                   observed_cause_reproduced=True)
        assert summarize([row])['wire_grouping_both_gates_fit'] == 0
        assert summarize([row])['wire_grouping_token_rejections_bypassed'] == 0
        assert payload == before


def test_wire_grouping_fallback_counts_original_request_when_guidance_costs_more():
    with database() as connection:
        _, payload, settings = synthetic(connection)
        payload['memories'] = payload['memories'][:1]
        measured = inspect_payload(payload, settings)
        assert not measured['wire_grouping']['applied']
        assert measured['wire_grouping']['messages_utf8_bytes'] == measured['messages_utf8_bytes']
        assert measured['wire_grouping']['input_token_estimate'] == measured['input_token_estimate']
        assert measured['wire_grouping']['saved_bytes'] == 0


def test_doubled_threshold_scenarios_partition_all_inputs_at_inclusive_boundaries():
    from tools.m5.level_c_input_diagnostics import threshold_scenario
    rows = [dict(messages_utf8_bytes=b, input_token_estimate=t, stratum='ordinary', conversation_id='conv-26')
            for b,t in [(320000,96000), (320001,96000), (320000,96001), (320001,192001), (319999,192000)]]
    before = deepcopy(rows)
    a = threshold_scenario(rows,320000,96000)
    b = threshold_scenario(rows,320000,192000)
    assert (a['summary']['feasible'],a['summary']['byte_only_exceeded'],a['summary']['token_only_exceeded'],a['summary']['both_exceeded']) == (1,1,2,1)
    assert (b['summary']['feasible'],b['summary']['byte_only_exceeded'],b['summary']['token_only_exceeded'],b['summary']['both_exceeded']) == (3,1,0,1)
    for scenario in (a,b):
        summary = scenario['summary']
        assert summary['feasible'] + summary['infeasible'] == summary['items'] == 5
        assert sum(scenario['by_stratum'][key]['items'] for key in ('ordinary','diagnostic')) == 5
        assert sum(group['items'] for group in scenario['by_conversation'].values()) == 5
        assert scenario['by_conversation']['conv-42']['items'] == 0
        assert not scenario['model_success_evaluated'] and not scenario['production_configuration_changed']
        assert not scenario['rerun_authorized'] and not scenario['increased_budget_authorized']
    assert rows == before


_FROZEN_TEMPLATE = None


def frozen_proposal(proposal):
    # Run the 200-item synthetic pipeline once; each mutation gets an isolated
    # copy of that stable fixture, avoiding repeated mock generations.
    global _FROZEN_TEMPLATE
    origin, output, _ = proposal
    if _FROZEN_TEMPLATE is not None:
        cached_origin, cached_output = _FROZEN_TEMPLATE
        wal = cached_output/'memory.sqlite3-wal'
        assert not wal.exists() or wal.stat().st_size == 0
        copied = output.parent/'frozen-copy'
        shutil.copytree(cached_output, copied, ignore=shutil.ignore_patterns('*-wal', '*-shm'))
        return cached_origin, copied
    import httpx
    write(output/'authorization.json', stage_tool.expected_authorization(output))
    stage_tool.execute(output, httpx.MockTransport(query_provider), ControlledEmbedder())
    _FROZEN_TEMPLATE = (origin, output)
    return origin, output


def test_complete_guarded_diagnostics_binds_plan_snapshot_and_never_opens_gold(proposal, monkeypatch):
    origin, output = frozen_proposal(proposal)
    from tools.m5 import level_c_audit
    import httpx
    from locomo_memory.model import DeepSeekModel
    def forbidden(*args, **kwargs):
        raise AssertionError('provider_or_network_must_not_run')
    monkeypatch.setattr(httpx, 'Client', forbidden)
    monkeypatch.setattr(DeepSeekModel, 'generate', forbidden)
    original_readonly = level_c_audit.readonly
    def no_reference_db(path):
        assert path.resolve() != origin.resolve()
        return original_readonly(path)
    monkeypatch.setattr(level_c_audit, 'readonly', no_reference_db)
    before = {path:hashlib.sha256(path.read_bytes()).hexdigest() for path in output.rglob('*') if path.is_file() and not path.name.endswith(('-wal','-shm'))}
    result = run(output)
    after = {path:hashlib.sha256(path.read_bytes()).hexdigest() for path in output.rglob('*') if path.is_file() and not path.name.endswith(('-wal','-shm'))}
    # SQLite may materialize empty WAL/shared-memory bookkeeping even in mode=ro;
    # compare persistent bytes and rely on the protected logical digest for DB state.
    assert before == after
    integrity = result['input_integrity']
    assert integrity['complete_frozen_items'] == integrity['planned_items'] == 200
    assert integrity['before_after_full_audit_equal'] and integrity['initial_logical_snapshot_reconstructed']
    assert integrity['producer_identities_verified'] and integrity['frozen_settings_and_inputs_verified']
    assert integrity['protected_snapshot_sha256'] == json.loads((output/'plan.json').read_text())['database_snapshot']
    assert result['summary']['items'] == result['summary']['both_fit'] == 100
    assert result['reconstruction']['frozen_token_audit_matches'] == 100
    assert result['provider_calls'] == 0 and not result['gold_read'] and not result['holdout_read']
    assert 'HIDDEN_GOLD' not in json.dumps(result) and 'HIDDEN_EVIDENCE' not in json.dumps(result)
    assert all(part['items'] == 25 for part in result['by_conversation'].values())
    assert not result['reconstruction']['wire_capture_available']
    assert not result['offline_probe']['model_noninferiority_evaluated']


@pytest.mark.parametrize('mutation', ['source_whitespace', 'missing_plan', 'partial_freeze', 'settings', 'inputs', 'producer'])
def test_guard_rejects_byte_tampering_or_incomplete_freeze_even_if_tokens_match(proposal, mutation):
    _, output = frozen_proposal(proposal)
    if mutation == 'source_whitespace':
        item = json.loads((output/'items/000-dynamic.json').read_text())
        with readonly(output/'memory.sqlite3') as connection:
            before = inspect_payload(first_resolve_payload(item, connection), Settings.model_validate(item['trace']['config']))
        with sqlite3.connect(output/'memory.sqlite3') as connection:
            connection.execute("UPDATE source_turns SET text=text||'     '")
        with readonly(output/'memory.sqlite3') as connection:
            after = inspect_payload(first_resolve_payload(item, connection), Settings.model_validate(item['trace']['config']))
        assert before['input_token_estimate'] == after['input_token_estimate']
        assert before['messages_utf8_bytes'] < after['messages_utf8_bytes']
        assert before['messages_sha256'] != after['messages_sha256']
        expected = 'audit_frozen_build_or_source_changed'
    elif mutation == 'missing_plan':
        (output/'plan.json').rename(output/'removed-plan.json')
        with pytest.raises(FileNotFoundError):
            run(output)
        return
    elif mutation == 'partial_freeze':
        path = output/'generation-freeze.json'; freeze = json.loads(path.read_text())
        freeze['item_hashes'] = {name:value for name,value in freeze['item_hashes'].items() if name.endswith('-dynamic.json')}
        path.write_text(json.dumps(freeze)); expected = 'generation_not_completely_frozen'
    elif mutation == 'settings':
        path = output/'settings.json'; settings = json.loads(path.read_text())
        settings['model_temperature'] = 0.1; path.write_text(json.dumps(settings)); expected = 'level_c_plan_changed'
    elif mutation == 'inputs':
        path = output/'inputs.json'; inputs = json.loads(path.read_text())
        inputs[0]['question'] += ' '; path.write_text(json.dumps(inputs)); expected = 'level_c_plan_changed'
    else:
        path = output/'plan.json'; plan = json.loads(path.read_text())
        plan['implementation_sha256']['src/locomo_memory/model.py'] = '0'*64
        path.write_text(json.dumps(plan)); expected = 'level_c_plan_changed'
    with pytest.raises(ValueError, match=f'^{expected}$'):
        run(output)


def test_guard_rechecks_database_after_reconstruction(proposal, monkeypatch):
    _, output = frozen_proposal(proposal)
    from tools.m5 import level_c_input_diagnostics as diagnostics
    original = diagnostics.first_resolve_payload
    changed = False
    def mutate_after_read(item, connection):
        nonlocal changed
        payload = original(item, connection)
        if not changed:
            # WAL allows an independent writer while reconstruction retains its
            # own earlier snapshot. The final existing audit must catch this.
            with sqlite3.connect(output/'memory.sqlite3') as writer:
                writer.execute("UPDATE source_turns SET text=text||'     '")
            changed = True
        return payload
    with sqlite3.connect(output/'memory.sqlite3') as connection:
        connection.execute('PRAGMA journal_mode=WAL')
    monkeypatch.setattr(diagnostics, 'first_resolve_payload', mutate_after_read)
    with pytest.raises(ValueError, match='^audit_frozen_build_or_source_changed$'):
        run(output)
