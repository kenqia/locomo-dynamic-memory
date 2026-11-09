"""Bounded diagnostics fail closed before an unplanned or repeated provider send."""
import json

import httpx

from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder
from locomo_memory.api import create_app
from fastapi.testclient import TestClient


def test_fixed_retrieval_query_replay_uses_public_pipeline_without_extra_analysis(settings, sample, tmp_path):
    from tools.m5.live_boundary_worker import replay_query

    source_model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=source_model, embedder=ControlledEmbedder())) as client:
        dataset, bid = complete_build(client, sample)
        trace = client.post('/queries', json={'dataset_id': dataset, 'sample_id':'conv-a',
            'build_id':bid, 'strategy':'dynamic', 'question':'Where did Alex live during April 2023?'}).json()
        source_ids = {sid for c in trace['expanded']['candidates'] for sid in c['memory']['source_ids']}
        sources = client.get(f'/datasets/{dataset}/conversations/conv-a/turns').json()['items']
        # Read the public citation endpoint response rather than private storage.
        assert all('source_id' in source for source in sources)
    observed = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        observed.append(payload)
        return query_provider(request)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    packet = dict(question_id='conv-a:qa:0', question=trace['question'], sample_id='conv-a',
        dataset_id=dataset, build_id=bid, initial=trace['initial'], expanded=trace['expanded'],
        relations=trace['relations'], config=settings.snapshot(), sources=sources)
    result = replay_query(packet, settings, model, tmp_path/'replay.sqlite3')
    assert result['outcome']=='succeeded'
    assert [p['operation'] for p in observed]==['resolve','answer']
    assert result['time']['query_interval']['start']=='2023-04-01'
    assert {s['source_id'] for s in observed[0]['sources']}==source_ids
