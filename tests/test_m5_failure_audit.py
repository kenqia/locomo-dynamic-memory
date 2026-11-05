import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.m5_queries import query
from locomo_memory.model import DeepSeekModel
from locomo_memory.queries import QueryFailure
from locomo_memory.query_schemas import QueryRequest
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def prepared(settings, sample):
    adapter = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    app = create_app(settings, model=adapter, embedder=ControlledEmbedder())
    return app, adapter


def test_graph_budget_failure_has_saved_trace(settings, sample):
    app, _ = prepared(settings, sample)
    with TestClient(app) as client:
        dataset, build = complete_build(client, sample)
        with pytest.raises(QueryFailure) as failure:
            query(app.state.queries, QueryRequest(dataset_id=dataset, sample_id='conv-a', build_id=build,
                                                question='Where does Alex live now?'), graph_depth=2, graph_token_budget=1)
        trace = app.state.queries.get(failure.value.trace_id)
        assert trace['outcome'] == 'failed'
        assert trace['error']['code'] == 'm5_graph_scope_or_budget_invalid'
        assert trace['m5_variant']['graph_depth'] == 2


def test_provider_budget_rejection_has_saved_trace(settings, sample, tmp_path):
    app, adapter = prepared(settings, sample)
    with TestClient(app) as client:
        dataset, build = complete_build(client, sample)
        adapter._transport = BudgetTransport(tmp_path/'zero.sqlite3',httpx.MockTransport(query_provider),
            max_requests=0,max_usd='0',model='deepseek-flash',input_usd_per_million='.3',
            output_usd_per_million='1.2',max_input_bytes=1000000,max_output_tokens=8192)
        with pytest.raises(QueryFailure) as failure:
            query(app.state.queries, QueryRequest(dataset_id=dataset,sample_id='conv-a',build_id=build,
                                                question='Where does Alex live now?'), temporal=True)
        trace = app.state.queries.get(failure.value.trace_id)
        assert trace['outcome'] == 'failed' and trace['error']['code'] == 'physical_request_budget_exhausted'
        assert trace['operations']['query_analysis']['calls'] == []


def test_temporal_operator_and_relative_provenance(settings, sample):
    app, _ = prepared(settings, sample)
    with TestClient(app) as client:
        dataset, build = complete_build(client, sample)
        for question in ('Where did Alex live before 2023-05-02?', 'Where did Alex live between May 1 2023 and May 2 2023?'):
            trace = query(app.state.queries, QueryRequest(dataset_id=dataset,sample_id='conv-a',build_id=build,
                                                        question=question), temporal=True)
            assert trace['time']['requested_date'] is None
            assert trace['time']['origin'] == 'm5_temporal_operator_preserved'
            assert trace['m5_temporal_intent']['original_question'] == question
        trace = query(app.state.queries,QueryRequest(dataset_id=dataset,sample_id='conv-a',build_id=build,
                                                   question='Where did Alex live yesterday?'),temporal=True)
        assert trace['time']['requested_date'] == '2023-05-01'
        assert trace['time']['origin'] == 'm5_relative_to_conversation_cutoff'
        assert 'Paris' in trace['answer']['answer']
