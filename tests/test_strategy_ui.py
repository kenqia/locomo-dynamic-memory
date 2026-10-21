"""Exercise actual Streamlit switches and source reads without model calls."""
from streamlit.testing.v1 import AppTest


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
