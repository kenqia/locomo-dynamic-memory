"""Public-source controlled query regressions, with QA gold excluded from generation.

These check evidence delivery and enforced contracts, not live model semantics.
"""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft
from test_raw_queries import published
from test_retrieval import ControlledEmbedder


CASES = {
    'qa3': dict(turns=['D2:8', 'D17:8'], question='What did Caroline research?',
                content='Caroline is researching adoption agencies.', value='adoption agencies',
                answer='Adoption agencies.', gap='Research start date is unknown'),
    'qa13': dict(turns=['D4:11', 'D7:5'], question="What career path has Caroline decided to persue?",
                 content='Caroline is considering counseling or mental health work.', value='counseling or mental health',
                 answer='Counseling or mental health work (considering).', gap='A completed career decision is not confirmed'),
    'qa15': dict(turns=['D2:5', 'D5:6'], question='What activities does Melanie partake in?',
                 content='Melanie runs, reads and plays the violin.', value='running, reading, violin',
                 answer='Running, reading, playing the violin, and pottery.', gap='Other activities she is a fan of may be missing'),
    'qa157': dict(turns=['D4:3'], question="What does Melanie's necklace symbolize?",
                  content="Caroline's necklace stands for love, faith and strength.", value='love, faith and strength',
                  answer='No information available.', gap="No evidence of Melanie's necklace"),
    'qa53': dict(turns=['D13:1'], question='When did Caroline apply to adoption agencies?',
                 content='Caroline applied to adoption agencies this week.', value='applied',
                 answer='The week containing 23 August 2023.', gap=None),
}


@pytest.mark.parametrize('case_id', CASES)
def test_public_source_answer_regressions(settings, case_id):
    case = CASES[case_id]
    fixture = json.loads((Path(__file__).parent / 'fixtures/answer-source-turns.json').read_text())
    turns = {s['dia_id']: s for s in fixture['turns']}
    conversation = {'speaker_a': 'Caroline', 'speaker_b': 'Melanie'}
    for did in case['turns']:
        n = did.split(':')[0][1:]
        source = turns[did]
        conversation[f'session_{n}_date_time'] = source['session_time']
        conversation[f'session_{n}'] = [{k: source[k] for k in ('dia_id', 'speaker', 'text')}]
    sample = [{'sample_id': 'conv-a', 'conversation': conversation}]
    observed = []

    def provider(request):
        body = json.loads(request.content)
        payload = json.loads(body['messages'][1]['content'])
        op = payload.get('operation')
        observed.append((op, payload))
        if op is None and 'sources' in payload:
            source = next(s for s in payload['sources'] if s['dia_id'] == case['turns'][0])
            time = {} if case_id != 'qa53' else {
                'original_expression': 'this week', 'anchor_source_id': source['source_id'],
                'event_start': '2023-08-21', 'event_end': '2023-08-27',
                'basis': 'Calendar week containing the source date; exact day unknown'}
            return completion({'memories': [draft([source['source_id']], content=case['content'],
                entity_id='Melanie' if case_id == 'qa15' else 'Caroline', state_dimension='activity',
                state_value=case['value'], statement_type='plan' if case_id == 'qa13' else 'fact', time=time)]})
        if op == 'resolve_raw':
            memory = payload['memories'][0]
            mids = [] if case_id == 'qa157' else [memory['memory_id']]
            recovered = [s['source_id'] for s in payload['raw_sources'] if s['dia_id'] == 'D5:6'] if case_id == 'qa15' else []
            status = 'sufficient' if case_id == 'qa53' or recovered else 'insufficient'
            coverage = [{'question': case['question'], 'status': status, 'memory_ids': mids,
                         'source_ids': recovered, 'gap': None if status == 'sufficient' else case['gap']}]
            # A supported first item plus an unresolved detail reproduces the QA 3 fallback pattern.
            if case_id == 'qa3':
                coverage = [dict(question=case['question'], status='sufficient', memory_ids=mids, source_ids=[], gap=None),
                            dict(question='When did the research start?', status='insufficient', memory_ids=[], source_ids=[], gap=case['gap'])]
            return completion({'status': status, 'effective_memory_ids': mids, 'effective_source_ids': recovered,
                'decisions': [{'memory_id': memory['memory_id'], 'selected': bool(mids),
                               'reason': 'Query subject is Melanie, source subject is Caroline' if not mids else 'Supported fact, with original modality'}],
                'coverage': coverage, 'explanation': 'Check attribution, modality and partial support', 'supplemental_relations': []})
        if op == 'answer_raw':
            if case_id == 'qa3':
                assert any('adoption agencies' in m['content'] for m in payload['memories'])
            if case_id == 'qa13':
                assert payload['memories'][0]['statement_type'] == 'plan'
            if case_id == 'qa15':
                assert payload['memories'] and any(s['dia_id'] == 'D5:6' for s in payload['raw_sources'])
            if case_id == 'qa157':
                assert not payload['memories'] and not payload['raw_sources']
            if case_id == 'qa53':
                source = payload['sources'][0]
                assert source['session_time'] == '3:31 pm on 23 August, 2023'
                assert 'this week' in source['text']
                assert 'week containing' in body['messages'][0]['content']
            citations = [{'memory_id': m['memory_id'], 'source_ids': m['source_ids']} for m in payload['memories']]
            citations += [{'memory_id': None, 'source_ids': [s['source_id']]} for s in payload['raw_sources']]
            return completion({'status': payload['status'], 'answer': case['answer'], 'citations': citations,
                               'explanation': "The necklace source concerns Caroline, not Melanie." if case_id == 'qa157' else case['gap']})
        if 'new_memory' in payload:
            return completion({'judgments': []})
        return completion({'entities': [], 'topic': None, 'time': None, 'keywords': []})

    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        query = {**published(client, sample), 'question': case['question']}
        response = client.post('/queries', json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['answer']['answer'] == case['answer']
        if case_id == 'qa15':
            assert trace['initial_resolution']['status'] == 'insufficient'
            assert trace['answer']['status'] == 'sufficient'
            assert len(trace['answer']['citations']) == 2
        elif case_id == 'qa53':
            assert trace['answer']['status'] == 'sufficient'
            assert not trace['raw_fallback']['triggered']
        elif case_id == 'qa157':
            assert trace['answer']['status'] == 'insufficient'
            assert not trace['answer']['citations']
        else:
            assert trace['answer']['status'] == 'insufficient'
            assert trace['answer']['citations'][0]['memory_id'] == trace['initial_resolution']['effective_memory_ids'][0]
        for op, payload in observed:
            assert 'gold' not in payload and 'qa' not in payload and 'answer' not in payload


@pytest.mark.parametrize('strategy', ['dynamic', 'dynamic_raw_fallback'])
@pytest.mark.parametrize('support', ['none', 'background_only', 'partial'])
def test_answer_prompt_distinguishes_requested_support_from_related_background(settings, sample, strategy, support):
    sample[0]['conversation']['session_2'][0]['text'] = 'Maybe I will adopt in October.'
    question = 'Where does Alex live and what adoption plans did Alex have in summer?' if support == 'partial' else 'What adoption plans did Alex have in summer?'
    answer_prompts = []

    def provider(request):
        body = json.loads(request.content)
        payload = json.loads(body['messages'][1]['content'])
        op = payload.get('operation')
        if op is None and 'sources' in payload and 'new_memory' not in payload:
            sources = payload['sources']
            return completion({'memories': [draft([sources[0]['source_id']]),
                draft([sources[-1]['source_id']], content='Alex might adopt in October.',
                      statement_type='uncertain', state_dimension='adoption_plan', state_value='October')]})
        if 'new_memory' in payload:
            from test_relations import relation
            return completion({'judgments': [relation(old, payload['new_memory']) for old in payload['history']]})
        if op in ('resolve', 'resolve_raw'):
            # Background may be selected by resolution, but does not answer summer plans.
            selected = [m for m in payload['memories'] if support != 'none' and
                        (support == 'partial' or m['state_dimension'] == 'adoption_plan')]
            mids = [m['memory_id'] for m in selected]
            result = {'status': 'insufficient', 'effective_memory_ids': mids,
                'decisions': [{'memory_id': m['memory_id'], 'selected': m['memory_id'] in mids,
                               'reason': 'Partial evidence or related background'} for m in payload['memories']],
                'explanation': 'No supported summer plans', 'supplemental_relations': []}
            if op == 'resolve_raw':
                result.update(effective_source_ids=[], coverage=[{'question': question, 'status': 'insufficient',
                    'memory_ids': mids, 'source_ids': [], 'gap': 'Summer plans unsupported'}])
            return completion(result)
        if op in ('answer', 'answer_raw'):
            prompt = body['messages'][0]['content']
            answer_prompts.append(prompt)
            assert 'Related background alone is not a partial answer' in prompt
            assert 'person, time and requested fact' in prompt
            assert 'Do not replace all insufficient answers with abstention' in prompt
            residence = [m for m in payload['memories'] if m['state_dimension'] == 'residence']
            citations = [{'memory_id': m['memory_id'], 'source_ids': m['source_ids']} for m in residence]
            return completion({'status': 'insufficient', 'answer': 'Paris.' if residence else 'No information available.',
                'explanation': 'October intent does not establish summer plans.', 'citations': citations})
        return completion({'entities': [], 'topic': None, 'time': None, 'keywords': []})

    local = settings.model_copy(update={'model_retries': 0})
    model = DeepSeekModel(local, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(local, model=model, embedder=ControlledEmbedder())) as client:
        query = {**published(client, sample), 'strategy': strategy, 'question': question}
        response = client.post('/queries', json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert len(answer_prompts) == 1
        assert trace['answer']['answer'] == ('Paris.' if support == 'partial' else 'No information available.')
        assert bool(trace['answer']['citations']) is (support == 'partial')
        assert trace['answer']['explanation'] == 'October intent does not establish summer plans.'
        if support == 'background_only':
            assert trace['effective_memories']  # Topic relevance must not count as a supported subanswer.


@pytest.mark.parametrize('strategy', ['dynamic', 'dynamic_raw_fallback'])
@pytest.mark.parametrize('expression,anchor,start,end', [
    ('this week', '23 August, 2023', '2023-08-21', '2023-08-27'),
    ('last week', '23 August, 2023', '2023-08-14', '2023-08-20'),
    ('yesterday', '8 May, 2023', '2023-05-07', '2023-05-07'),
    ('last Friday', '14 August, 2023', '2023-08-11', '2023-08-11'),
])
def test_query_uses_source_anchor_over_wrong_legacy_time(settings, sample, strategy, expression, anchor, start, end):
    sample[0]['conversation']['session_1_date_time'] = '1:00 pm on ' + anchor
    sample[0]['conversation']['session_2_date_time'] = '1:00 pm on ' + anchor
    sample[0]['conversation']['session_1'][0]['text'] = 'I applied ' + expression + '.'
    observed = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        op = payload.get('operation')
        if op is None and 'sources' in payload and 'new_memory' not in payload:
            sid = payload['sources'][0]['source_id']
            return completion({'memories': [draft([sid], content='Alex applied ' + expression + '.',
                time=dict(original_expression=expression, anchor_source_id=sid, event_start='2000-01-01',
                          event_end='2000-01-02', basis='the week preceding that session'))]})
        if op in ('resolve', 'resolve_raw', 'answer', 'answer_raw'):
            observed.append(op)
            memory = payload['memories'][0]
            assert memory['time']['event_start'] == start
            assert memory['time']['event_end'] == end
            assert 'preceding' not in memory['time']['basis']
            if op in ('resolve', 'resolve_raw'):
                result = dict(status='sufficient', effective_memory_ids=[memory['memory_id']],
                    decisions=[dict(memory_id=memory['memory_id'], selected=True, reason='Anchored source')],
                    explanation='Original relative expression')
                if op == 'resolve_raw':
                    result.update(effective_source_ids=[], coverage=[dict(question=payload['question'], status='sufficient',
                        memory_ids=[memory['memory_id']], source_ids=[])])
                return completion(result)
            return completion(dict(status=payload['status'], answer=start, citations=[
                dict(memory_id=memory['memory_id'], source_ids=memory['source_ids'])]))
        return completion(dict(entities=[], topic=None, time=None, keywords=[]))
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model, embedder=ControlledEmbedder())) as client:
        query = {**published(client, sample), 'strategy':strategy, 'question':'When did Alex apply?'}
        response = client.post('/queries', json=query)
        assert response.status_code == 201, response.text
        trace = response.json()
        assert trace['time_diagnostics'][0]['reason'] == 'source_relative_time_overrides_derived_time'
        assert len(observed) == 2
        original = client.get(f"/builds/{query['build_id']}/memories").json()['items'][0]
        assert original['time']['event_start'] == '2000-01-01'
