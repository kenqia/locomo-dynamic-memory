"""Exercise production API/UI with research boundaries that fail if invoked."""
import importlib
import json
import sys

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder


def forbid_research(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Default Build/API/UI invoked a research or raw-only boundary')

    boundaries = {
        'source_answer_reader': ['SourceAnswerReader.generate'],
        'revised_source_reader': ['RevisedSourceReader.generate'],
        'selective_context': ['predecessor_context'],
        'source_context': ['source_window'],
        'evidence_catalog': ['EvidenceCatalog.__init__'],
        'proposition_extraction': ['bind_proposition'],
        'extraction_patch': ['apply_patches'],
        'ablation': ['AblationService.prepare', 'AblationService.execute'],
        'raw_queries': ['run_raw_query', 'pack_payload'],
        'raw_retrieval': ['pinned_sources'],
    }
    for module, names in boundaries.items():
        module = importlib.import_module('locomo_memory.' + module)
        for name in names:
            owner = module
            parts = name.split('.')
            for part in parts[:-1]:
                owner = getattr(owner, part)
            monkeypatch.setattr(owner, parts[-1], forbidden)


@pytest.mark.parametrize('via_ui', [False, True])
def test_default_build_api_ui_use_only_approved_operations(settings, sample, monkeypatch, via_ui):
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])
    forbid_research(monkeypatch)
    operations = []

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        operation = payload.get('operation') or (
            'relate' if 'new_memory' in payload else 'extract' if 'sources' in payload else 'query_analysis')
        operations.append(operation)
        return query_provider(request)

    model = DeepSeekModel(settings, api_key='synthetic-only', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset, bid = complete_build(client, sample)
        assert 'extract' in operations and 'relate' in operations
        operations.clear()
        if via_ui:
            app = AppTest.from_string('''
import streamlit as st
from locomo_memory.query_ui import render_queries
render_queries(st.session_state['request'], st.session_state['dataset'], 'conv-a',
               {'build_id': st.session_state['bid'], 'query_ready': True})
''')
            def request(method, path, **kwargs):
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()
            for key, value in {'request': request, 'dataset': dataset, 'bid': bid}.items():
                app.session_state[key] = value
            app.run()
            assert not app.exception and app.selectbox[0].value == 'dynamic'
            app.text_input[0].set_value('Where does Alex live?').run()
            assert operations == []
            app.button[0].click().run()
            assert not app.exception
            trace = app.session_state['effective_result']
        else:
            response = client.post('/queries', json={'dataset_id': dataset, 'sample_id': 'conv-a',
                                                     'question': 'Where does Alex live?'})
            assert response.status_code == 201, response.text
            trace = response.json()
        assert operations == ['query_analysis', 'resolve', 'answer']
        assert trace['answer']['answer'] == 'Alex lives in Rome.'
        assert trace['config']['resolution_input_budget'] == 24000
        assert trace['resolution_budgets']['resolve']['within_budget']
        assert not trace['resolution_budgets']['resolve']['truncated']
        assert 'raw_fallback' not in trace and 'strategy_recovery' not in trace
        assert client.get('/queries/' + trace['trace_id']).json() == trace


def test_invalid_default_resolution_never_invokes_research_or_raw_fallback(settings, sample, monkeypatch):
    from test_builds import completion
    forbid_research(monkeypatch)
    attempted = []

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'resolve':
            attempted.append(payload)
            return completion({'status': 'sufficient', 'effective_memory_ids': ['foreign-memory'],
                               'decisions': [], 'explanation': 'Synthetic rejected scope'})
        return query_provider(request)

    local = settings.model_copy(update={'model_retries': 1})
    model = DeepSeekModel(local, api_key='synthetic-only', transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        dataset, bid = complete_build(client, sample)
        response = client.post('/queries', json={'dataset_id': dataset, 'sample_id': 'conv-a',
                                                 'question': 'Where does Alex live?'})
        assert response.status_code == 502
        trace = client.get('/queries/' + response.json()['error']['trace_id']).json()
        assert trace['build_id'] == bid
        assert trace['error'] == {'stage': 'resolve', 'code': 'invalid_output'}
        assert len(attempted) == len(trace['operations']['resolve']['calls']) == 2
        assert 'retry_feedback' in attempted[1]
        assert trace['usage_summary']['generation_calls'] == 3
        assert 'answer' not in trace and 'strategy_recovery' not in trace


def test_service_validation_failure_keeps_completed_provider_usage(settings, sample, monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace

    forbid_research(monkeypatch)
    model = DeepSeekModel(settings, api_key='synthetic-only', transport=httpx.MockTransport(query_provider))
    generate = model.generate

    def adapter(operation, *args, **kwargs):
        result = generate(operation, *args, **kwargs)
        if operation == 'resolve':
            # Exercise the service's validation independently of the adapter.
            value = result.value.model_dump(mode='json')
            value['effective_memory_ids'] = ['foreign-memory']
            return replace(result, value=SimpleNamespace(model_dump=lambda **kw: value))
        return result

    monkeypatch.setattr(model, 'generate', adapter)
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        dataset, _ = complete_build(client, sample)
        response = client.post('/queries', json={'dataset_id': dataset, 'sample_id': 'conv-a',
                                                 'question': 'Where does Alex live?'})
        assert response.status_code == 502
        trace = client.get('/queries/' + response.json()['error']['trace_id']).json()
        assert trace['error'] == {'stage': 'resolve', 'code': 'invalid_output'}
        assert len(trace['operations']['resolve']['calls']) == 1
        delivery = trace['resolution_budgets']['resolve']['source_delivery']
        assert delivery['status'] == 'request_attempted'
        assert delivery['delivered_source_ids'] == delivery['expected_source_ids']
        assert trace['usage_summary']['generation_calls'] == 2
