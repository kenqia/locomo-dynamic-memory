"""Temporal scope stays distinct from a single date and from reporting time."""
from datetime import date
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from locomo_memory.temporal import explicit_question_date, question_interval
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


@pytest.mark.parametrize('question', [
    'Where did Alex live before 2023-05-02?',
    'Where did Alex move after May 1, 2023?',
    'Where did Alex live since 1 May 2023?',
])
def test_temporal_operator_is_not_an_exact_query_date(question):
    assert explicit_question_date(question) is None


@pytest.mark.parametrize('strategy', ['dynamic', 'hybrid_no_resolution'])
def test_month_range_reaches_resolver_and_answer_without_source_time_filter(settings, sample, strategy):
    observed = []

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') in {'resolve', 'answer'}:
            observed.append(payload)
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset, bid = complete_build(client, sample)
        response = client.post('/queries', json=dict(dataset_id=dataset, sample_id='conv-a',
            build_id=bid, strategy=strategy, question='Where did Alex live during April 2023?'))
        assert response.status_code == 201, response.text
        timing = response.json()['time']
        assert timing['requested_date'] is None
        assert timing['query_interval'] == dict(start='2023-04-01', end='2023-04-30',
                                               precision='month', start_inclusive=True, end_inclusive=True)
        if strategy == 'dynamic':
            assert timing['origin'] == 'explicit_question_interval'
        assert all(p['time'] == timing for p in observed)
        # May reports can describe April reality. Neither retrieval nor resolve drops them by report time.
        if strategy == 'dynamic':
            assert len(observed[0]['memories']) == 2
        assert explicit_question_date('Where did Alex live on May 1, 2023?') == date(2023, 5, 1)


@pytest.mark.parametrize('question, expected', [
    ('during February 2024', ('2024-02-01', '2024-02-29')),
    ('during Feb 2023', ('2023-02-01', '2023-02-28')),
    ('before 2023-05-02', (None, '2023-05-02')),
    ('since May 1, 2023', ('2023-05-01', None)),
    ('between July 2023 and August 2023', None),
    ('from 2023-07-01 to 2023-07-31', None),
])
def test_supported_intervals_preserve_precision_and_ambiguous_ranges_stay_unknown(question, expected):
    interval = question_interval(question)
    assert ((interval['start'], interval['end']) if interval else None) == expected
