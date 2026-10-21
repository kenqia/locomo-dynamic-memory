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
