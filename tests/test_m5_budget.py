import json
import sqlite3

import httpx
import pytest

from locomo_memory.m5_budget import BudgetTransport
from locomo_memory.model import ModelFailure
from locomo_memory.model import DeepSeekModel
from locomo_memory.config import Settings
from locomo_memory.retrieval_schemas import QueryAnalysis


def test_concurrent_transports_share_one_physical_request_slot(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    path = tmp_path/'shared.sqlite3'
    calls = []
    policy = dict(max_requests=1, max_usd='1', model='deepseek-flash',
                  input_usd_per_million='.3', output_usd_per_million='1.2',
                  max_input_bytes=10000, max_output_tokens=100)
    def provider(request):
        calls.append(1)
        return httpx.Response(200, json={'usage': {}})
    guards = [BudgetTransport(path, httpx.MockTransport(provider), **policy) for _ in range(2)]
    barrier = Barrier(2)
    def attempt(guard):
        barrier.wait()
        request = httpx.Request('POST', 'https://api.deepseek.com/chat/completions',
            json=dict(model='deepseek-flash', messages=[], max_tokens=1))
        try:
            guard.handle_request(request)
            return 'sent'
        except ModelFailure as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, guards))
    assert sorted(outcomes) == ['physical_request_budget_exhausted', 'sent']
    assert len(calls) == 1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT COUNT(*) FROM physical_requests').fetchone()[0] == 1


def test_amount_cap_rejects_before_count_cap_and_retains_unknown_reservation(tmp_path):
    path = tmp_path/'amount.sqlite3'
    calls = []
    def provider(request):
        calls.append(1)
        raise httpx.ReadTimeout('synthetic unknown usage')
    guard = BudgetTransport(path, httpx.MockTransport(provider), max_requests=100, max_usd='.000002',
        model='deepseek-flash', input_usd_per_million='.3', output_usd_per_million='1.2',
        max_input_bytes=10000, max_output_tokens=100)
    request = httpx.Request('POST', 'https://api.deepseek.com/chat/completions',
        json=dict(model='deepseek-flash', messages=[], max_tokens=1))
    with pytest.raises(httpx.ReadTimeout):
        guard.handle_request(request)
    with pytest.raises(ModelFailure, match='budget_exhausted'):
        guard.handle_request(request)
    assert len(calls) == 1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT reserved_usd,status FROM physical_requests').fetchall() == [
            ('0.0000018', 'transport_unknown')]


def test_global_physical_request_cap_survives_restart_and_unknown_usage(tmp_path):
    count = []
    def provider(request):
        count.append(1)
        if len(count) == 1:
            raise httpx.ReadTimeout('synthetic timeout')
        return httpx.Response(200, json={'usage': {}})
    policy = dict(max_requests=2,max_usd='1',model='deepseek-flash',input_usd_per_million='.3',
                  output_usd_per_million='1.2',max_input_bytes=10000,max_output_tokens=100)
    path = tmp_path/'ledger.sqlite3'
    delegate = httpx.MockTransport(provider)
    request = httpx.Request('POST','https://api.deepseek.com/chat/completions',json=dict(
        model='deepseek-flash',messages=[{'role':'user','content':'synthetic'}],max_tokens=50))
    guard = BudgetTransport(path,delegate,**policy)
    with pytest.raises(httpx.ReadTimeout):
        guard.handle_request(request)
    restarted = BudgetTransport(path,delegate,**policy)
    restarted.handle_request(request)
    with pytest.raises(ModelFailure, match='budget_exhausted'):
        restarted.handle_request(request)
    assert len(count) == 2
    with sqlite3.connect(path) as db:
        assert {r[0] for r in db.execute('SELECT status FROM physical_requests')} == {'transport_unknown','response_usage_unknown'}
    with pytest.raises(ValueError, match='policy_changed'):
        BudgetTransport(path,delegate,**{**policy,'max_requests':3})


def test_zero_budget_prevents_provider_and_policy_rejects_overlong(tmp_path):
    calls = []
    policy = dict(max_requests=0,max_usd='0',model='deepseek-flash',input_usd_per_million='.3',
                  output_usd_per_million='1.2',max_input_bytes=100,max_output_tokens=100)
    guard = BudgetTransport(tmp_path/'zero.sqlite3', httpx.MockTransport(lambda r: calls.append(r)), **policy)
    request = httpx.Request('POST','https://api.deepseek.com/chat/completions',json=dict(
        model='deepseek-flash',messages=[],max_tokens=1))
    with pytest.raises(ModelFailure, match='budget_exhausted'):
        guard.handle_request(request)
    request = httpx.Request('POST','https://api.deepseek.com/chat/completions',json=dict(
        model='deepseek-flash',messages=['x'*101],max_tokens=1))
    with pytest.raises(ModelFailure, match='policy_rejected'):
        guard.handle_request(request)
    assert not calls


def test_budget_stop_preserves_prior_physical_failure_without_retry(tmp_path):
    calls = []
    def provider(request):
        calls.append(1)
        return httpx.Response(503)
    guard = BudgetTransport(tmp_path/'one.sqlite3', httpx.MockTransport(provider),
        max_requests=1, max_usd='1', model='deepseek-flash', input_usd_per_million='.3',
        output_usd_per_million='1.2', max_input_bytes=100000, max_output_tokens=8192)
    model = DeepSeekModel(Settings(model_retries=5), api_key='synthetic-only', transport=guard)
    with pytest.raises(ModelFailure) as failure:
        model.generate('query_analysis', {'question': 'Synthetic question?'}, QueryAnalysis)
    assert failure.value.code == 'physical_request_budget_exhausted'
    assert len(failure.value.metadata['calls']) == len(calls) == 1
    assert failure.value.metadata['calls'][0]['http_status'] == 503
