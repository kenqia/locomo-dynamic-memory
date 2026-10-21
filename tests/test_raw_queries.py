import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_retrieval import ControlledEmbedder, build


def raw_provider(observed, *, enough=False, partial=False):
    def provider(request):
        body = json.loads(request.content)
        payload = json.loads(body["messages"][1]["content"])
        operation = payload.get("operation")
        observed.append((operation, payload, body["messages"]))
        if operation == "resolve_raw":
            raw = payload.get("raw_sources", [])
            relevant = [s for s in raw if "Cedar" in s["text"]]
            mids = [m["memory_id"] for m in payload["memories"]] if enough else []
            sids = [s["source_id"] for s in relevant]
            known = enough or bool(sids)
            return completion({"status": "sufficient" if known else "insufficient",
                "effective_memory_ids": mids, "effective_source_ids": sids,
                "decisions": [{"memory_id": m["memory_id"], "selected": m["memory_id"] in mids, "reason": "Direct question evidence" if enough else "Residence does not answer employment"} for m in payload["memories"]],
                "coverage": [{"question": payload["question"], "status": "insufficient" if partial else "sufficient" if known else "insufficient", "memory_ids": mids, "source_ids": sids, "gap": "Missing start date" if partial else None if known else "Missing employment evidence"}],
                "explanation": "Check the supplied sources", "supplemental_relations": []})
        if operation == "answer_raw":
            raw = payload.get("raw_sources", [])
            if raw:
                citations = [{"memory_id": None, "source_ids": [s["source_id"] for s in raw if "Cedar" in s["text"]]}]
            else:
                citations = [{"memory_id": m["memory_id"], "source_ids": m["source_ids"]} for m in payload["memories"]]
            return completion({"status": payload["status"], "answer": "Alex works for Cedar; start date is unknown." if partial else "Alex works for Cedar." if raw else "Alex lives in Paris.", "citations": citations})
        if operation is None and "sources" in payload:
            return completion({"memories": [draft([payload["sources"][0]["source_id"]])]})
        return completion({"entities": ["Alex"], "topic": None, "time": None, "keywords": []})
    return provider


def test_raw_fallback_restores_unextracted_fact_with_citation_and_pinned_source_trace(settings, sample):
    sample[0]["conversation"]["session_2"][0]["text"] = "I work for Cedar."
    observed = []
    model = DeepSeekModel(settings, api_key="synthetic-test-key", transport=httpx.MockTransport(raw_provider(observed)))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        bid = build(client, sample)
        client.post(f"/builds/{bid}/index")
        client.post(f"/builds/{bid}/relations")
        assert client.post(f"/builds/{bid}/publish").status_code == 200
        dataset = client.get(f"/builds/{bid}").json()["dataset_id"]
        state = client.get(f"/builds/{bid}/current-state").json()
        response = client.post("/queries", json={"dataset_id": dataset, "sample_id": "conv-a", "strategy": "dynamic_raw_fallback", "question": "Where does Alex work?"})
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace["answer"]["status"] == "sufficient"
        assert trace["answer"]["citations"] == [{"memory_id": None, "source_ids": [f"{dataset}/conv-a/D2:1"]}]
        assert trace["raw_fallback"]["triggered"] is True
        assert trace["raw_fallback"]["source_snapshot_sha256"]
        assert len([op for op, _, _ in observed if op == "resolve_raw"]) == 2
        assert trace["evidence_budget"]["token_count"] <= settings.evidence_token_budget
        assert trace["raw_fallback"]["token_count"] <= 2000
        assert client.get(f"/builds/{bid}/current-state").json() == state
        assert client.get(f"/queries/{trace['trace_id']}").json() == trace


def published(client, sample):
    bid = build(client, sample)
    assert client.post(f'/builds/{bid}/index').status_code == 201
    assert client.post(f'/builds/{bid}/relations').status_code == 202
    assert client.post(f'/builds/{bid}/publish').status_code == 200
    dataset = client.get(f'/builds/{bid}').json()['dataset_id']
    return {'dataset_id': dataset, 'sample_id': 'conv-a', 'build_id': bid, 'strategy': 'dynamic_raw_fallback', 'question': 'Where does Alex work?'}


@pytest.mark.parametrize('profile', ['expanded','focused'])
def test_new_evaluation_strategy_reports_mixed_source_coverage_without_memory_truth(settings, sample, profile):
    sample[0]['conversation']['session_2'][0]['text'] = 'I work for Cedar.'
    observed = []
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(raw_provider(observed)))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        query = published(client, sample)
        inputs = client.post('/evaluation-inputs', json={'dataset_id': query['dataset_id'], 'samples': [{'sample_id': 'conv-a', 'question': query['question'], 'answer': 'Cedar', 'evidence': ['D2:1'], 'category': 4}]}).json()
        response = client.post('/evaluation-runs', json={'wait': True, 'input_id': inputs['input_id'], 'strategies': ['dynamic_raw_fallback'], 'evidence_profile':profile, 'build_ids': {'conv-a': query['build_id']}})
        assert response.status_code == 201, response.text
        run = response.json()
        row = run['results'][0]
        assert row['source_coverage']['answer_context'] == 1
        assert row['source_sets']['answer_context'] == [f"{query['dataset_id']}/conv-a/D2:1"]
        assert row['ranking_units']['answer_context'] == 'Memory + SourceTurn'
        assert row['dynamic_metric']['value'] is None
        assert row['usage_summary']['embedding_calls'] == 1
        assert run['raw_fallback']['resolution_prompt']
        assert run['raw_fallback']['evidence_profile'] == profile
        assert row['trace']['evidence_selection']['profile'] == profile


@pytest.mark.parametrize('enough,partial,text,expected,rounds,triggered', [
    (True, False, 'I work for Cedar.', 'sufficient', 1, False),
    (True, True, 'I work for Cedar.', 'insufficient', 2, True),
    (False, True, 'I work for Cedar.', 'insufficient', 2, True),
    (False, False, 'Zebra quartz violet.', 'insufficient', 1, True),
])
def test_coverage_controls_one_bounded_fallback_and_partial_answers(settings, sample, enough, partial, text, expected, rounds, triggered):
    sample[0]['conversation']['session_2'][0]['text'] = text
    if 'Zebra' in text:
        sample[0]['conversation']['session_1'][0]['text'] = 'Amber ruby.'
        sample[0]['conversation']['session_1'][1]['text'] = 'Blue green.'
    observed = []
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(raw_provider(observed, enough=enough, partial=partial)))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        query = published(client, sample)
        response = client.post('/queries', json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['answer']['status'] == expected
        assert trace['raw_fallback']['triggered'] == triggered
        assert len([op for op,_,_ in observed if op == 'resolve_raw']) == rounds
        if partial:
            assert trace['answer']['citations']
            assert 'unknown' in trace['answer']['answer']
        assert all(b['input_token_count'] <= 12000 for b in trace['resolution_budgets'].values())
        if not triggered:
            assert not trace['raw_fallback']['source_ids']


@pytest.mark.parametrize('mode', ['raw_raw_conflict', 'memory_raw_conflict', 'foreign_raw', 'foreign_citation'])
def test_mixed_conflict_citations_and_source_scope(settings, sample, mode):
    sample[0]['conversation']['session_1'][0]['text'] = 'I work for Cedar.'
    sample[0]['conversation']['session_2'][0]['text'] = 'I do not work for Cedar.'
    observed = []
    original = raw_provider(observed)
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        operation = payload.get('operation')
        if operation == 'resolve_raw' and payload['raw_sources']:
            mids = [m['memory_id'] for m in payload['memories']][:1] if mode == 'memory_raw_conflict' else []
            sids = [s['source_id'] for s in payload['raw_sources'] if 'Cedar' in s['text']]
            if mids:
                sids = sids[-1:]
            if mode == 'foreign_raw':
                sids = ['other/conversation/D1:1']
            status = 'sufficient' if mode in ('foreign_raw', 'foreign_citation') else 'conflict'
            return completion({'status': status, 'effective_memory_ids': mids, 'effective_source_ids': sids,
                'decisions': [{'memory_id':m['memory_id'], 'selected':m['memory_id'] in mids, 'reason':'Retain conflicting source'} for m in payload['memories']],
                'coverage':[{'question':payload['question'],'status':status,'memory_ids':mids,'source_ids':sids,'gap':None}],
                'explanation':'Contradictory original sources', 'supplemental_relations':[]})
        if operation == 'answer_raw':
            citations = [{'memory_id': m['memory_id'], 'source_ids':m['source_ids']} for m in payload['memories']]
            citations += [{'memory_id':None, 'source_ids':[s['source_id']]} for s in payload['raw_sources']]
            if mode == 'foreign_citation':
                citations = [{'memory_id':None, 'source_ids':['other/conversation/D1:1']}]
            return completion({'status':payload['status'], 'answer':'Employment evidence remains contradictory.', 'citations':citations})
        return original(request)
    settings = settings.model_copy(update={'model_retries':0})
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        query = published(client, sample)
        response = client.post('/queries', json=query)
        if mode.startswith('foreign'):
            assert response.status_code == 502, response.text
            trace = client.get('/queries/' + response.json()['error']['trace_id']).json()
            assert trace['error']['code'] == 'invalid_output'
            delivery = trace['source_delivery'] if mode == 'foreign_citation' else trace['resolution_budgets']['joint_resolve']['source_delivery']
            assert delivery['status'] == 'request_attempted'
        else:
            assert response.status_code == 201, response.text
            assert response.json()['answer']['status'] == 'conflict'
            assert len(response.json()['answer']['citations']) == 2


@pytest.mark.parametrize('limits,expected_rounds,expected_status', [
    ({'raw_token_budget': 1}, 1, 'insufficient'),
    ({'evidence_token_budget': 1}, 2, 'insufficient'),
    ({'resolution_input_budget': 100}, 0, None),
])
def test_serialized_budgets_fail_closed_and_keep_delivery_auditable(settings, sample, limits, expected_rounds, expected_status):
    sample[0]['conversation']['session_2'][0]['text'] = 'I work for Cedar.'
    observed = []
    settings = settings.model_copy(update=limits)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(raw_provider(observed)))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        response = client.post('/queries', json=published(client, sample))
        if expected_status is None:
            assert response.status_code == 422, response.text
            trace = client.get('/queries/' + response.json()['error']['trace_id']).json()
            assert trace['error']['code'] == 'fixed_query_input_budget_exceeded'
        else:
            assert response.status_code == 201, response.text
            trace = response.json()
            assert trace['answer']['status'] == expected_status
            assert trace['raw_fallback']['token_count'] <= settings.raw_token_budget
            assert trace['evidence_budget']['token_count'] <= settings.evidence_token_budget
            assert trace['source_delivery']['delivered_source_ids'] == []
        assert len([op for op,_,_ in observed if op == 'resolve_raw']) == expected_rounds


def test_raw_windows_skip_oversized_centers_deduplicate_and_stay_in_pinned_conversation(settings, sample):
    from copy import deepcopy
    sample[0]['conversation']['session_1'] = [
        {'dia_id':f'D1:{i+1}', 'speaker':'Alex', 'text':text} for i,text in enumerate([
            'gigantic ' * 3000, 'Cedar colleague.', 'gigantic I work for Cedar.', 'Cedar office.', 'Cedar hours.'])]
    other = deepcopy(sample[0])
    other['sample_id'] = 'conv-b'
    for turn in other['conversation']['session_1']:
        turn['text'] = 'Cedar OTHER-CONVERSATION-SECRET'
    sample.append(other)
    sample[0]['conversation']['session_2'][0]['text'] = 'Work session two.'
    observed = []
    settings = settings.model_copy(update={'raw_max_hits':2, 'raw_max_turns':9, 'raw_token_budget':500})
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(raw_provider(observed)))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        query = {**published(client, sample), 'question':'gigantic'}
        # Same conversation name in a later import must not change an explicit build pin.
        from conftest import import_sample
        newer = deepcopy(sample[:1])
        newer[0]['conversation']['session_2'][0]['text'] = 'Cedar NEW-IMPORT-SECRET'
        assert import_sample(client, newer).status_code == 201
        response = client.post('/queries', json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        fallback = trace['raw_fallback']
        assert len(fallback['source_ids']) <= 3
        assert len(fallback['source_ids']) == len(set(fallback['source_ids']))
        assert fallback['centers'] <= 2
        assert any(o['source_id'].endswith('/D1:1') and o['reason']=='raw_token_budget' for o in fallback['omitted'])
        assert all(s.startswith(query['dataset_id'] + '/conv-a/') for s in fallback['source_ids'])
        requests = [p for op,p,_ in observed if op in ('resolve_raw','answer_raw')]
        assert 'OTHER-CONVERSATION-SECRET' not in json.dumps(requests)
        assert 'NEW-IMPORT-SECRET' not in json.dumps(requests)
        assert all(not any(s['source_id'].endswith('/D2:1') for s in p['raw_sources']) for p in requests)


def test_raw_query_keeps_original_pin_when_active_version_changes_during_analysis(settings, sample):
    sample[0]['conversation']['session_2'][0]['text'] = 'I work for Cedar.'
    observed, switch = [], {}
    base = raw_provider(observed)
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if switch.get('armed') and payload.get('operation') is None and 'sources' not in payload:
            switch['armed'] = False
            assert switch['client'].post(f"/builds/{switch['new']}/publish").status_code == 200
        return base(request)
    model = DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        query = published(client,sample)
        newer = build(client,sample)
        assert client.post(f'/builds/{newer}/index').status_code == 201
        assert client.post(f'/builds/{newer}/relations').status_code == 202
        switch.update(client=client,new=newer,armed=True)
        response = client.post('/queries',json={k:v for k,v in query.items() if k!='build_id'})
        assert response.status_code == 201, response.text
        assert response.json()['build_id'] == query['build_id']
        pin = client.get('/versions/pin',params={'dataset_id':query['dataset_id'],'sample_id':'conv-a'}).json()
        assert pin['build_id'] == newer
        assert response.json()['raw_fallback']['pinned_source_ids']


def test_explicit_context_rejection_is_recorded_as_provider_refusal(settings,sample):
    sample[0]['conversation']['session_2'][0]['text'] = 'I work for Cedar.'
    observed = []
    base = raw_provider(observed)
    def provider(request):
        p = json.loads(json.loads(request.content)['messages'][1]['content'])
        if p.get('operation') == 'answer_raw':
            return httpx.Response(400,json={'error':{'code':'context_length_exceeded','message':'synthetic refusal'}})
        return base(request)
    settings = settings.model_copy(update={'model_retries':0})
    model = DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        response = client.post('/queries',json=published(client,sample))
        assert response.status_code == 502, response.text
        trace = client.get('/queries/' + response.json()['error']['trace_id']).json()
        assert trace['error'] == {'code':'context_length_exceeded','stage':'answer'}
        assert trace['source_delivery']['status'] == 'request_attempted'
        assert trace['source_delivery']['attempted_source_ids']
        assert trace['source_delivery']['provider_accepted'] is False
        assert trace['evidence_budget']['context_limit_exceeded'] is True


@pytest.mark.parametrize('requested_date', [None, '2024-01-01'])
def test_controller_always_exposes_known_time_boundary_even_when_model_omits_it(settings,sample,requested_date):
    observed = []
    model = DeepSeekModel(settings,api_key='synthetic-test-key',transport=httpx.MockTransport(raw_provider(observed,enough=True)))
    with TestClient(create_app(settings,model=model,embedder=ControlledEmbedder())) as client:
        response = client.post('/queries',json={**published(client,sample),'requested_date':requested_date})
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['time']['cutoff'] in trace['answer']['answer']
        assert 'later reality is unknown' in trace['answer']['answer'].lower()
        assert trace['answer_boundary']['applied_by'] == 'controller'
        if requested_date:
            assert trace['answer']['status'] == 'insufficient'


def test_raw_search_truncation_can_still_deliver_a_complete_answer(settings, sample):
    sample[0]['conversation']['session_2'][0]['text'] = 'I work for Cedar.'
    sample[0]['conversation']['session_1'][1]['text'] = 'I work near Cedar office.'
    observed = []
    local = settings.model_copy(update={'raw_max_hits': 1, 'raw_neighbor_turns': 0})
    model = DeepSeekModel(local, api_key='synthetic-test-key', transport=httpx.MockTransport(raw_provider(observed)))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        response = client.post('/queries', json=published(client, sample))
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['raw_fallback']['truncated'] is True
        assert trace['resolution']['status'] == 'sufficient'
        assert trace['answer']['status'] == 'sufficient'
        assert trace['answer']['citations']
