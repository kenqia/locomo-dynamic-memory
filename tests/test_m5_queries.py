import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.m5_queries import query
from locomo_memory.query_schemas import QueryRequest
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def test_temporal_priority_uses_explicit_request_date_over_question_cutoff(tmp_path):
    from contextlib import contextmanager
    from datetime import date
    import json
    import sqlite3
    from types import SimpleNamespace
    from locomo_memory.m5_queries import BonusRetrieval

    path = tmp_path/'candidates.sqlite3'
    @contextmanager
    def connect():
        with sqlite3.connect(path) as db:
            yield db
    database = SimpleNamespace(connect=connect)
    with connect() as db:
        db.execute('CREATE TABLE candidate_queries(query_id TEXT,build_id TEXT,result_json TEXT)')
    candidates = [dict(memory=dict(memory_id=mid, entity_id='Alex', time=timing)) for mid, timing in (
        ('current', dict(valid_from='2023-05-02')),
        ('historical', dict(valid_from='2023-05-01', valid_to='2023-05-01')))]
    base = SimpleNamespace(settings=None, database=database, query=lambda *_: dict(
        query_id='original', analysis={'result': {}}, initial_candidates=candidates))
    bundle = SimpleNamespace(projection=SimpleNamespace(cutoff='2023-05-02T00:00:00'))
    result = BonusRetrieval(base, bundle, temporal=True, requested_date=date(2023,5,1)).query(
        'build', 'Where does Alex live now?')
    assert [item['memory']['memory_id'] for item in result['initial_candidates']] == ['historical', 'current']
    assert result['m5_interval']['basis'] == 'explicit_request_date'
    assert result['m5_interval']['start'] == result['m5_interval']['end'] == '2023-05-01'
    with connect() as db:
        saved = json.loads(db.execute('SELECT result_json FROM candidate_queries').fetchone()[0])
    assert saved['m5_interval'] == result['m5_interval']


@pytest.mark.parametrize('options', [{}, {'graph_depth': 2}, {'adaptive': True}, {'temporal': True}])
def test_bonus_query_reuses_real_resolution_answer_and_pinned_sources(settings, sample, options):
    adapter = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    app = create_app(settings, model=adapter, embedder=ControlledEmbedder())
    with TestClient(app) as client:
        dataset_id, build_id = complete_build(client, sample)
        original = client.get(f'/builds/{build_id}/export').json()
        result = query(app.state.queries, QueryRequest(dataset_id=dataset_id, sample_id='conv-a',
                       build_id=build_id, question='Where does Alex live now?'), **options)
        assert result['outcome'] == 'succeeded'
        assert result['answer']['answer'] == 'Alex lives in Rome.'
        assert client.get(f'/queries/{result["trace_id"]}').json() == result
        assert client.get(f'/builds/{build_id}/export').json() == original
        if options.get('graph_depth'):
            assert result['expanded']['m5_graph']['depth'] == 2
        if options.get('adaptive'):
            assert result['initial']['m5_route']['kind'] == 'state'
