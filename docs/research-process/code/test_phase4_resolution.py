from copy import deepcopy

import pytest

from tools.research_v2.resolution_planner import (
    decode, digest, encode, execute_mock, plan, plan_opt_in, preservation_gate,
)


def evidence():
    return {'question': 'When did Coco arrive, and did the third turtle arrive?',
        'analysis': {'time': None}, 'candidates_truncated': True,
        'memories': [
            {'memory_id': 'm1', 'source_ids': ['s1'], 'state_key': 'pets', 'content': 'Plans to adopt Coco.',
             'statement_type': 'plan', 'polarity': 'positive', 'time': {'anchor_source_id': 's1', 'original_expression': 'last week'}},
            {'memory_id': 'm2', 'source_ids': ['s2'], 'state_key': 'pets', 'content': 'Shadow arrived; Coco did not.',
             'statement_type': 'fact', 'polarity': 'negative', 'time': None},
            {'memory_id': 'm3', 'source_ids': ['s3'], 'state_key': 'turtles', 'content': 'A third turtle arrived.',
             'statement_type': 'fact', 'polarity': 'positive', 'future_field': {'values': [None, False], '@': 0}}],
        'sources': [{'source_id': 's1', 'text': 'I plan to adopt Coco last week.', 'session_time': '2023-04-10'},
                    {'source_id': 's2', 'text': 'Shadow arrived; Coco did not.'},
                    {'source_id': 's3', 'text': 'I now have three turtles.'}],
        'relations': [{'relation_id': 'r1', 'old_memory_id': 'm1', 'new_memory_id': 'm2', 'label': 'undetermined',
                       'source_ids': ['s1', 's2'], 'applicability': {'condition_satisfied': False}}]}


def test_exact_roundtrip_keeps_missing_null_false_unknown_and_event_distinctions():
    original = evidence()
    encoded = encode(original)
    restored = decode(encoded)
    assert restored == original
    assert 'future_field' not in restored['memories'][0]
    assert restored['memories'][1]['time'] is None
    assert restored['relations'][0]['applicability']['condition_satisfied'] is False
    gate = preservation_gate(original, restored)
    assert gate['passed'] and gate['input_candidates_truncated']
    assert gate['semantic_correctness'] == 'not_evaluated'
    restored['memories'][0]['time']['original_expression'] = 'today'
    assert original['memories'][0]['time']['original_expression'] == 'last week'
    assert not preservation_gate(original, restored)['passed']


@pytest.mark.parametrize('field', ['content', 'source_ids', 'time', 'statement_type', 'polarity'])
def test_gate_rejects_loss_of_each_critical_semantic_field(field):
    original = evidence(); changed = deepcopy(original)
    del changed['memories'][0][field]
    assert 'roundtrip_field_mismatch' in preservation_gate(original, changed)['errors']


@pytest.mark.parametrize('change,error', [
    ('source', 'missing_memory_source'), ('endpoint', 'missing_relation_endpoint'),
    ('anchor', 'missing_memory_time_anchor'), ('condition', 'missing_relation_source_or_anchor'),
    ('duplicate', 'duplicate_or_missing_memory_id'),
])
def test_existing_missing_dependencies_fail_closed_even_with_exact_roundtrip(change, error):
    original = evidence()
    if change == 'source': original['sources'].pop(0)
    if change == 'endpoint': original['relations'][0]['new_memory_id'] = 'absent'
    if change == 'anchor': original['memories'][0]['time']['anchor_source_id'] = 'absent'
    if change == 'condition': original['relations'][0]['applicability']['condition_source_ids'] = ['absent']
    if change == 'duplicate': original['memories'].append(deepcopy(original['memories'][0]))
    candidate = plan(original)
    assert candidate.status == 'incomplete'
    assert error in candidate.failure_reasons


def test_column_dictionary_shares_exact_values_without_merging_independent_objects():
    original = evidence()
    original['memories'] = [dict(original['memories'][0], memory_id=f'm{i}') for i in range(30)]
    original['relations'] = []
    encoded = encode(original)
    assert any('dictionary' in col for col in encoded['tables']['memories']['columns'])
    assert decode(encoded) == original
    assert len(decode(encoded)['memories']) == 30


def test_budget_failure_never_calls_resolver_and_disabled_path_is_identity():
    original = evidence()
    assert plan_opt_in(original) is original
    candidate = plan_opt_in(original, enabled=True, input_budget=1)
    def mock(*args): raise AssertionError('must not call')
    mock.mock_only = True
    result = execute_mock(original, candidate, mock)
    assert result['status'] == 'incomplete' and result['calls'] == 0


def test_mock_receives_restored_full_evidence_and_tampering_is_rejected():
    original = evidence(); candidate = plan(original)
    def mock(messages, restored):
        assert restored == original and 'Reconstruct each input table' in messages[0]['content']
        return {'unresolved_event_link': ['m1', 'm2']}
    with pytest.raises(ValueError, match='mock_resolver_required'):
        execute_mock(original, candidate, mock)
    mock.mock_only = True
    assert execute_mock(original, candidate, mock)['status'] == 'mock_completed'
    candidate.representation['context']['question'] = 'changed'
    with pytest.raises(ValueError, match='representation_identity_changed'):
        execute_mock(original, candidate, mock)
    with pytest.raises(ValueError, match='original_identity_changed'):
        execute_mock(dict(original, question='changed'), candidate, mock)


def test_invalid_dictionary_index_cannot_alias_the_last_fact():
    original = evidence(); original['memories'] *= 30
    encoded = encode(original)
    column = next(c for c in encoded['tables']['memories']['columns'] if 'indices' in c)
    column['indices'][0] = -1
    with pytest.raises(ValueError, match='invalid_dictionary_reference'):
        decode(encoded)


def test_request_identity_binds_question_budget_representation_and_response_schema():
    original = evidence()
    first = plan(original)
    assert first.request_identity == plan(deepcopy(original)).request_identity
    assert first.request_identity != plan(original, input_budget=95000).request_identity
    assert first.request_identity != plan(dict(original, question='other')).request_identity
    assert first.original_sha256 == digest(original)


def test_mutated_budget_or_ready_flag_cannot_bypass_preflight():
    original = evidence(); candidate = plan(original)
    def mock(*args): raise AssertionError('must not call')
    mock.mock_only = True
    candidate.config['input_budget'] = 1
    with pytest.raises(ValueError, match='request_identity_changed'):
        execute_mock(original, candidate, mock)
    candidate = plan(original, input_budget=1)
    candidate.status = 'ready_for_mock'; candidate.within_budget = True
    assert execute_mock(original, candidate, mock)['status'] == 'incomplete'


def test_real_queryservice_mock_injection_keeps_answer_and_default_rollback(settings, sample):
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.model import DeepSeekModel
    from locomo_memory.query_schemas import QueryRequest
    from tools.research_v2.resolution_planner import MockResolutionPlanner
    from test_queries import complete_build, query_provider
    from test_retrieval import ControlledEmbedder

    operations = []
    def provider(request):
        import json
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        operations.append(payload.get('operation'))
        return query_provider(request)

    def resolver(messages, original):
        return {'status': 'sufficient', 'effective_memory_ids': [m['memory_id'] for m in original['memories'] if m['state_value'] == 'Rome'],
            'decisions': [{'memory_id': m['memory_id'], 'selected': m['state_value'] == 'Rome', 'reason': 'Mock cutoff'} for m in original['memories']],
            'supplemental_relations': [], 'explanation': 'Mock source-bound temporal contract'}
    resolver.mock_only = True
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset, bid = complete_build(client, sample); service = client.app.state.queries
        request = QueryRequest(dataset_id=dataset, sample_id='conv-a', build_id=bid, question='Where does Alex live?')
        control = service.query(request); operations.clear()
        research = service.query(request, research_resolution_planner=MockResolutionPlanner(resolver))
        assert 'resolve' not in operations
        assert research['answer'] == control['answer']
        assert research['effective_memories'] == control['effective_memories']
        assert research['research_resolution_plan']['preservation']['passed']
        assert research['resolution_budgets']['resolve']['source_delivery']['status'] == 'offline_mock_accepted'
        assert research['query_fingerprint'] != control['query_fingerprint']
        rollback = service.query(request)
        assert 'research_resolution_plan' not in rollback
        assert rollback['answer'] == control['answer']
        assert rollback['query_fingerprint'] == control['query_fingerprint']
        # Exercise the actual branch where original preflight fails but an exact
        # encoded packet fits; no fake budget counter or provider is substituted.
        from locomo_memory.model import request_token_estimate
        from locomo_memory.query_schemas import EffectiveResolution
        from locomo_memory.queries import QueryFailure
        from tools.research_v2.phase4_offline import reconstruct
        large = deepcopy(control['expanded'])
        for i in range(80):
            item = deepcopy(large['candidates'][i % 2])
            item['memory']['memory_id'] = f'synthetic-extra-{i}'
            large['candidates'].append(item)
        with service.database.connect() as db:
            full = reconstruct(db, {**control, 'expanded': large}, request.question)
        control_count = request_token_estimate('resolve', full, EffectiveResolution)
        encoded_count = plan(full).estimated_input_tokens
        assert encoded_count < control_count
        service.settings.resolution_input_budget = (encoded_count + control_count)//2
        service.expansion.expand = lambda *args, **kwargs: deepcopy(large)
        with pytest.raises(QueryFailure, match='complete_resolution_input_budget_exceeded'):
            service.query(request)
        rescued = service.query(request, research_resolution_planner=MockResolutionPlanner(resolver))
        assert not rescued['resolution_budgets']['resolve']['within_budget']
        assert rescued['research_resolution_plan']['within_budget']
        assert rescued['research_resolution_plan']['preservation']['original_counts']['memories'] == 82
