"""Context can support a target fact without re-extracting neighboring facts."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import import_sample
from locomo_memory.api import create_app
from locomo_memory.model import DeepSeekModel
from test_builds import completion, draft


@pytest.mark.parametrize('context_only_output', [False, True])
def test_build_separates_context_from_target_and_rejects_neighbor_only_claims(settings, sample, context_only_output):
    settings = settings.model_copy(update={'fragment_turns': 1, 'model_retries': 0})
    observed = []

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        observed.append(payload)
        targets = payload['target_source_ids']
        sources = {s['source_id']: s for s in payload['sources']}
        if len(observed) == 2:
            assert any(s['dia_id'] == 'D1:1' for s in sources.values())
            previous = next(sid for sid, s in sources.items() if s['dia_id'] == 'D1:1')
            ids = [previous] if context_only_output else [previous, *targets]
            return completion({'memories': [draft(ids, content='Alex cancelled the plan to join Microsoft.',
                statement_type='plan', polarity='negative', state_dimension='employment')]})
        return completion({'memories': [], 'no_facts_reason': 'No target fact in this synthetic check'})

    sample[0]['conversation']['session_1'][0]['text'] = 'I plan to join Microsoft.'
    sample[0]['conversation']['session_1'][1]['text'] = 'But later I cancelled that plan.'
    sample[0]['conversation']['session_1'][1]['speaker'] = 'Alex'
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    with TestClient(create_app(settings, model=model)) as client:
        dataset = import_sample(client, sample).json()['dataset_id']
        response = client.post('/builds', json=dict(dataset_id=dataset, sample_id='conv-a', context_turns=1))
        assert response.status_code == 202, response.text
        bid = response.json()['build_id']
        result = client.get(f'/builds/{bid}').json()
        assert result['status'] == ('failed' if context_only_output else 'extracted')
        items = client.get(f'/builds/{bid}/memories').json()['items']
        assert len(items) == (0 if context_only_output else 1)
        if items:
            assert len(items[0]['source_ids']) == 2
        # A context window never crosses the original session boundary.
        assert all(len({s['session_id'] for s in p['sources']}) == 1 for p in observed)
