from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.m5_compression import expand
from locomo_memory.m5_ui import graph_dot
from test_retrieval import ControlledEmbedder
from test_versions import complete, model


def test_bonus_inspection_is_readonly_and_build_pinned(settings, sample):
    with TestClient(create_app(settings, model=model(settings), embedder=ControlledEmbedder())) as client:
        build_id = complete(client, sample)
        url = f'/builds/{build_id}'
        original = client.get(url + '/export').json()
        metadata = client.get(url + '/bonus/graph').json()
        assert metadata['entities'] == ['Alex']
        graph = client.get(url + '/bonus/graph', params={'root': 'entity:Alex', 'depth': 2}).json()
        assert 'SUPPORTED_BY' in graph_dot(graph)
        mid = original['memories'][0]['memory_id']
        assert client.post(url + '/bonus/graph-expand', json={'initial_ids': [mid]}).json()['memory_ids'] == [mid]
        assert client.post(url + '/bonus/graph-expand', json={'initial_ids': ['foreign']}).status_code == 422
        assert client.get(url + '/bonus/graph', params={'root': 'foreign'}).status_code == 422
        assert expand(client.get(url + '/bonus/compression').json()['package']) == original['memories']
        timeline = client.get(url + '/bonus/timeline', params={'entity': 'Alex', 'dimension': 'residence'}).json()
        assert timeline['build_id'] == build_id
        second = complete(client, sample)
        assert second != build_id
        assert client.get(url + '/export').json() == original
