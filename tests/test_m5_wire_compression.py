import json

import httpx

from locomo_memory.api import create_app
from locomo_memory.m5_queries import query
from locomo_memory.m5_wire_compression import group_wire, ungroup_wire, encode_request
from locomo_memory.model import DeepSeekModel
from locomo_memory.query_schemas import QueryRequest
from fastapi.testclient import TestClient
from test_queries import query_provider, complete_build
from test_retrieval import ControlledEmbedder


def test_wire_grouping_preserves_fields_order_and_counts_decoder():
    memories = [dict(memory_id=str(i), entity_id='Person', state_dimension='work', state_key='long-key-' * 20,
                     content=f'fact {i}', statement_type='plan' if i % 2 else 'fact', polarity='negative',
                     source_ids=[f's{i}'], time={'original_expression': 'last week'}) for i in range(40)]
    assert ungroup_wire(group_wire(memories)) == memories
    body = dict(messages=[{'role': 'system', 'content': 'JSON output'},
                          {'role': 'user', 'content': json.dumps({'operation': 'answer', 'memories': memories, 'sources': []})}])
    encoded, audit = encode_request(body)
    assert audit['applied'] and audit['sent_message_tokens'] < audit['original_message_tokens']
    assert ungroup_wire(json.loads(encoded['messages'][1]['content'])) == memories
    body['messages'][1]['content'] = json.dumps({'operation': 'answer', 'memories': memories[:1]})
    original, audit = encode_request(body)
    assert original is body and not audit['applied']


def test_optional_compressed_query_keeps_validation_and_sources(settings, sample):
    sent = []
    def provider(request):
        body = json.loads(request.content)
        payload = json.loads(body['messages'][1]['content'])
        if 'memory_groups_v1' in payload:
            payload['memories'] = ungroup_wire(payload)
            del payload['memory_groups_v1'], payload['memory_order']
            body['messages'][1]['content'] = json.dumps(payload)
            request = httpx.Request('POST', request.url, content=json.dumps(body))
        sent.append(payload)
        return query_provider(request)
    adapter = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    app = create_app(settings, model=adapter, embedder=ControlledEmbedder())
    with TestClient(app) as client:
        dataset, build = complete_build(client, sample)
        original = client.get(f'/builds/{build}/export').json()
        result = query(app.state.queries, QueryRequest(dataset_id=dataset, sample_id='conv-a', build_id=build,
                                                     question='Where does Alex live now?'), compression=True)
        assert result['answer']['answer'] == 'Alex lives in Rome.'
        assert result['m5_variant']['compression']
        assert result['operations']['answer']['m5_compression'][0]['roundtrip']
        assert client.get(f'/builds/{build}/export').json() == original
