"""Exercise actual Streamlit switches and source reads without model calls."""
from streamlit.testing.v1 import AppTest
import pytest


def test_query_strategy_switch_only_calls_backend_on_submit():
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.query_ui import render_queries
if 'calls' not in st.session_state:
    st.session_state['calls'] = []
def request(method, path, **kwargs):
    st.session_state['calls'].append((method, path, kwargs))
    return {'trace_id':'trace', 'build_id':'build', 'strategy':kwargs['json']['strategy'],
            'outcome':'succeeded', 'answer':{'status':'insufficient', 'answer':'No information available.', 'citations':[]},
            'time':{'cutoff_source_time':'22 October 2023'}, 'initial':{},'expanded':{},'resolution':{},
            'effective_memories':[], 'evidence_budget':{}}
render_queries(request, 'dataset', 'conv-26', {'build_id':'build', 'query_ready':True})
''').run()
    assert not app.exception
    app.radio[0].set_value('dynamic_raw_fallback').run()
    assert app.session_state['calls'] == []
    app.text_area[0].set_value('What does the necklace symbolize?')
    app.button[0].click().run()
    assert not app.exception
    assert len(app.session_state['calls']) == 1
    assert app.session_state['calls'][0][2]['json']['strategy'] == 'dynamic_raw_fallback'
    app.radio[0].set_value('dynamic').run()
    assert len(app.session_state['calls']) == 1


def test_saved_four_strategy_switches_and_sources_are_read_only():
    app = AppTest.from_string('''
import streamlit as st
from locomo_memory.evaluation_ui import render_saved_comparison
if 'calls' not in st.session_state:
    st.session_state['calls'] = []
def request(method, path, **kwargs):
    st.session_state['calls'].append((method, path))
    return {'speaker':'Caroline','session_time':'8 May 2023','text':'I went yesterday.'}
strategies = ['dynamic','dynamic_raw_fallback','hybrid_no_resolution','full_text']
rows = [{'sample_index':0,'strategy':s,'trace':{'answer':{
    'status':'sufficient','answer':s,'explanation':'Evidence explanation',
    'citations':[{'memory_id':None,'source_ids':['dataset/conv-26/D1:3']}]},
    'time':{'cutoff':'2023-10-22'}}} for s in strategies]
rows[-1] = {'sample_index':0,'strategy':'full_text','error':{'code':'invalid_output'}}
render_saved_comparison(request, {'input':{'samples':[{'question':'When?'}]},'strategies':strategies,'results':rows})
''').run()
    assert not app.exception
    for strategy in ['dynamic_raw_fallback', 'hybrid_no_resolution', 'full_text', 'dynamic']:
        app.radio[0].set_value(strategy).run()
        assert not app.exception
    assert app.session_state['calls'] == []
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['calls'] == [('GET', '/datasets/dataset/conversations/conv-26/turns/D1:3')]
    assert any(t.value == 'I went yesterday.' for t in app.text)


@pytest.mark.parametrize('strategy', ['dynamic_raw_fallback', 'dynamic'])
def test_recovered_partial_answer_and_sources_survive_in_streamlit(settings, sample, monkeypatch, strategy):
    """Render an actual query Trace after unsafe joint resolution, with no live calls."""
    import json
    import sys
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.model import DeepSeekModel
    from test_builds import completion
    from test_raw_queries import published, raw_provider
    from test_retrieval import ControlledEmbedder

    # AppTest replaces __main__; restore it before later multiprocessing spawn tests.
    monkeypatch.setitem(sys.modules, '__main__', sys.modules['__main__'])

    base = raw_provider([], enough=True, partial=True)

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'resolve':
            return completion({'invalid': 'Dynamic resolution cannot be validated'})
        if payload.get('operation') == 'resolve_raw' and payload['raw_sources']:
            return completion({'invalid': 'Joint resolution cannot be validated'})
        if payload.get('operation') == 'answer_raw':
            return completion({'status': 'insufficient', 'answer': 'Paris.',
                'explanation': 'Employment is unknown; new raw evidence remains unassessed.',
                'citations': [{'memory_id': m['memory_id'], 'source_ids': m['source_ids']}
                              for m in payload['memories']]})
        return base(request)

    local = settings.model_copy(update={'model_retries': 0})
    model = DeepSeekModel(local, api_key='synthetic-ui-only', transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        query = {**published(client, sample), 'strategy':strategy, 'question': 'Where does Alex live and work?'}
        response = client.post('/queries', json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['raw_fallback']['recovery']['code'] == 'invalid_output'
        assert trace['initial_resolution']['coverage'][0]['status'] == 'insufficient'
        app = AppTest.from_string('''
import streamlit as st
from locomo_memory.query_ui import render_queries
render_queries(st.session_state['request'], 'dataset', 'conv-a',
               {'build_id':st.session_state['effective_result']['build_id'], 'query_ready':True})
''')
        def request(method, path, **kwargs):
            result = client.request(method, path, **kwargs)
            result.raise_for_status()
            return result.json()
        app.session_state['request'] = request
        app.session_state['effective_result'] = trace
        app.run()
        assert not app.exception
        assert any(t.value == 'Paris.' for t in app.text)
        assert any(t.value == 'I live in Paris.' for t in app.text)
        assert any('unassessed' in c.value for c in app.caption)
        if strategy == 'dynamic':
            assert any('有界原文备用策略' in c.value for c in app.caption)
        assert any(m.value == '证据不足' for m in app.markdown)
        app.radio[0].set_value('dynamic_raw_fallback').run()
        assert not app.exception
        assert any(t.value == 'Paris.' for t in app.text)
