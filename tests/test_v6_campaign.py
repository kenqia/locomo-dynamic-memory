"""Budget and HTTP retry checks for the finite v6 experiment runner."""
import importlib.util
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from locomo_memory.model import DeepSeekModel, DiagnosticPersistenceFailure
from locomo_memory.relation_schemas import RelationBatch

spec = importlib.util.spec_from_file_location('v6_campaign', Path(__file__).resolve().parents[1] /
                                            'experiments/issue-15-v6-gates/v6_campaign.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Campaign = module.Campaign


def prior(tmp_path):
    path = tmp_path / 'prior.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE header(value TEXT);CREATE TABLE calls(sequence INTEGER);')
        db.execute('INSERT INTO header VALUES (?)', (json.dumps({'previous_calls': 9}),))
        db.executemany('INSERT INTO calls VALUES (?)', [(i,) for i in range(304)])
    return path


@pytest.mark.parametrize('available,expected', [(0, 0), (1, 1), (2, 2), (3, 3)])
def test_transient_retries_reserve_before_dispatch_and_respect_global_ceiling(tmp_path, settings, available, expected):
    budget = Campaign(tmp_path/'campaign.sqlite3', prior(tmp_path), create=True, limit=313+available)
    requests = []
    def provider(request):
        requests.append(True)
        # The reservation is visible before HTTP dispatch.
        assert budget.summary()['reserved_new_calls'] == len(requests)
        return httpx.Response(503, text='private-marker')
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    budget.bind(model, 'gate-1')
    with pytest.raises(DiagnosticPersistenceFailure):
        model.generate('relate', {}, RelationBatch)
    assert len(requests) == expected
    assert budget.summary()['reserved_total_calls'] == 313+expected
    restarted = Campaign(budget.path, budget.prior, limit=313+available)
    assert restarted.summary() == budget.summary()
    assert 'private-marker' not in budget.path.read_bytes().decode('latin1')


def test_transient_service_then_success_does_not_halt_next_operation(tmp_path, settings):
    budget = Campaign(tmp_path/'campaign.sqlite3', prior(tmp_path), create=True)
    replies = iter([httpx.Response(503), *[httpx.Response(200, json={
        'choices': [{'finish_reason': 'stop', 'message': {'content': '{"judgments": []}'}}]}) for _ in range(2)]])
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(lambda _: next(replies)))
    budget.bind(model, 'gate-1')
    model.generate('relate', {}, RelationBatch)
    model.generate('relate', {}, RelationBatch)
    assert budget.summary()['outcomes'] == {'model_http_error': 1, 'succeeded': 2}
    assert budget.summary()['reserved_total_calls'] == 316


def test_unknown_reservation_and_missing_history_block_further_dispatch(tmp_path):
    old = prior(tmp_path)
    budget = Campaign(tmp_path/'campaign.sqlite3', old, create=True)
    budget.reserve('gate-1', 'synthetic', 'relate')
    with pytest.raises(ValueError, match='unknown_call_requires_review'):
        budget.reserve('gate-1', 'synthetic', 'relate')
    with pytest.raises(ValueError, match='existing_campaign_required'):
        Campaign(tmp_path/'missing.sqlite3', old)
    with pytest.raises(ValueError, match='campaign_history_or_ceiling_changed'):
        Campaign(budget.path, old, limit=2000)


def test_balance_rejection_stops_without_retry_and_preserves_unknown_usage(tmp_path, settings):
    budget = Campaign(tmp_path/'campaign.sqlite3', prior(tmp_path), create=True)
    requests = []
    def provider(request):
        requests.append(True)
        return httpx.Response(402, text='private-marker')
    model = DeepSeekModel(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
    budget.bind(model, 'gate-2')
    for _ in range(2):
        with pytest.raises((DiagnosticPersistenceFailure, ValueError)):
            model.generate('relate', {}, RelationBatch)
    assert len(requests) == 1
    assert budget.summary()['reserved_total_calls'] == 314
    assert budget.summary()['usage']['calls_without_reported_usage'] == 1
