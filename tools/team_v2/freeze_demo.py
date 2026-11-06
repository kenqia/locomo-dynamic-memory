"""Export only newly generated synthetic API records into a public Replay bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'tests/browser')]


TRACE_FIELDS = ('trace_id', 'build_id', 'dataset_id', 'sample_id', 'question', 'strategy', 'outcome',
                'time', 'initial', 'expanded', 'resolution', 'effective_memories', 'answer', 'error',
                'evidence_budget', 'resolution_budgets', 'source_delivery', 'stage_seconds', 'usage_summary')
OMIT = {'config', 'model_metadata', 'prompts', 'answer_input', 'operations', 'request', 'response',
        'raw_response', 'raw_request', 'exact_wire', 'wire', 'headers', 'api_key'}


def public_record(value):
    if isinstance(value, dict):
        return {key: public_record(item) for key, item in value.items() if key not in OMIT}
    if isinstance(value, list):
        return [public_record(item) for item in value]
    return value


def export_fixture(output):
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.config import Settings
    from locomo_memory.model import DeepSeekModel
    from test_builds import completion, draft
    from test_relations import relation
    import server
    import numpy as np

    class ReplayEmbedder(server.BrowserEmbedder):
        def identity(self):
            return {**super().identity(), 'revision': 'replay-separated-topics-v1'}

        def encode(self, texts):
            vectors = np.zeros((len(texts), 384), dtype=np.float32)
            for index, text in enumerate(texts):
                lower = text.lower()
                axis = (2 if 'birth' in lower else 3 if 'tokyo' in lower else 4 if 'car' in lower
                        else 0 if 'paris' in lower and 'rome' not in lower else 1)
                vectors[index, axis] = 1
            return vectors

    server._failed_first_extraction = True
    sample = json.loads((ROOT / 'tests/browser/sample.json').read_text(encoding='utf-8'))
    sample[0]['conversation'].update(session_3_date_time='1:00 pm on 3 May, 2023', session_3=[
        {'dia_id': 'D3:1', 'speaker': 'Alex', 'text': 'I plan to visit Tokyo, but no date is decided.'},
        {'dia_id': 'D3:2', 'speaker': 'Alex', 'text': 'I do not own a car.'},
    ])

    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        if payload.get('operation') == 'answer' and 'citation anomaly' in payload['question']:
            memory = payload['memories'][0]
            return completion({'status': 'sufficient', 'answer': 'Rejected synthetic citation.',
                               'citations': [{'memory_id': memory['memory_id'], 'source_ids': ['invalid/conv-a/D9:9']}]})
        new = payload.get('new_memory')
        if new and (new['state_dimension'] in ('travel_plan', 'car_ownership') or
                    any(old['state_dimension'] != new['state_dimension'] for old in payload['history'])):
            return completion({'judgments': [relation(old, new) for old in payload['history']]})
        response = server.provider(request)
        if 'sources' in payload and 'new_memory' not in payload and 'operation' not in payload:
            envelope = response.json()
            data = json.loads(envelope['choices'][0]['message']['content'])
            for source in payload['sources']:
                if source['dia_id'] == 'D3:1':
                    data['memories'].append(draft([source['source_id']], content='Alex plans to visit Tokyo.',
                                                  statement_type='plan', state_dimension='travel_plan', state_value='Tokyo'))
                elif source['dia_id'] == 'D3:2':
                    data['memories'].append(draft([source['source_id']], content='Alex does not own a car.',
                                                  polarity='negative', state_dimension='car_ownership', state_value='car'))
            return completion(data)
        return response

    settings = Settings(db_path=output / 'memory.sqlite3', model_retries=0, initial_k=1)
    model = DeepSeekModel(settings, api_key='synthetic-freeze-only', transport=httpx.MockTransport(provider))
    snapshot = {'schema': 'public-console-replay-v1', 'mode': 'OFFLINE_SYNTHETIC_REPLAY',
                'datasets': [], 'conversations': [], 'builds': [], 'sources': [], 'memories': {},
                'relations': {}, 'projections': {}, 'traces': {}, 'cases': [], 'runs': []}

    def capture_case(client, kind, question, **extra):
        response = client.post('/queries', json={'dataset_id': dataset_id, 'sample_id': 'conv-a',
                               'build_id': build_id, 'question': question, **extra})
        assert response.status_code in (201, 422, 502), response.text
        trace_id = response.json().get('trace_id') or response.json()['error']['trace_id']
        trace = client.get(f'/queries/{trace_id}').json()
        if kind == 'citation_anomaly':
            assert trace['error']['code'] == 'invalid_output' and trace['error']['stage'] == 'answer', trace.get('error')
            codes = [call.get('error_code') for call in trace['operations']['answer']['calls']]
            assert 'answer_memory_citation_scope_required' in codes, codes
        if kind == 'budget_failure':
            assert trace['error']['code'] == 'conflict_evidence_budget_exceeded'
        if kind in ('success', 'historical', 'conflict', 'insufficient'):
            assert trace['outcome'] == 'succeeded', (kind, trace.get('error'))
            expected = {'success': 'sufficient', 'historical': 'sufficient', 'conflict': 'conflict', 'insufficient': 'insufficient'}[kind]
            assert trace['answer']['status'] == expected
        saved = public_record({key: trace[key] for key in TRACE_FIELDS if key in trace})
        saved['diagnostics'] = {operation: [{key: call.get(key) for key in
                               ('status', 'error_code', 'field_path', 'http_status', 'response_received')}
                               for call in metadata.get('calls', [])]
                                for operation, metadata in trace['operations'].items()}
        snapshot['traces'][trace_id] = saved
        snapshot['cases'].append({'case_id': kind, 'trace_id': trace_id, 'build_id': build_id,
                                  'question': question, 'outcome': trace['outcome'],
                                  'answer_status': trace.get('answer', {}).get('status'), 'error': trace.get('error')})

    with TestClient(create_app(settings, model=model, embedder=ReplayEmbedder())) as client:
        response = client.post('/imports', json={'data': sample, 'version': 'OFFLINE-SYNTHETIC-product-replay-v1',
                                                'license': 'synthetic-test-fixture'})
        assert response.status_code == 201, response.text
        dataset_id = response.json()['dataset_id']
        for _ in range(2):
            response = client.post('/builds', json={'dataset_id': dataset_id, 'sample_id': 'conv-a'})
            assert response.status_code == 202, response.text
            build_id = response.json()['build_id']
            for endpoint, expected in (('index', 201), ('relations', 202), ('publish', 200)):
                response = client.post(f'/builds/{build_id}/{endpoint}')
                assert response.status_code == expected, response.text
            snapshot['memories'][build_id] = client.get(f'/builds/{build_id}/memories?limit=100').json()['items']
            snapshot['relations'][build_id] = client.get(f'/builds/{build_id}/relations?limit=100').json()['items']
            snapshot['projections'][build_id] = client.get(f'/builds/{build_id}/current-state').json()
        snapshot['datasets'] = client.get('/datasets?limit=100').json()['items']
        snapshot['conversations'] = client.get(f'/datasets/{dataset_id}/conversations?limit=100').json()['items']
        snapshot['sources'] = client.get(f'/datasets/{dataset_id}/conversations/conv-a/turns?limit=100').json()['items']
        snapshot['builds'] = public_record(client.get('/builds?limit=100').json()['items'])
        for kind, question, extra in (
            ('success', 'Where does Alex live?', {}),
            ('historical', 'Where did Alex live?', {'requested_date': '2023-05-01'}),
            ('conflict', "What is Sam's birth year?", {}),
            ('insufficient', "What is Alex's passport number?", {}),
            ('citation_anomaly', 'Where does Alex live? citation anomaly', {}),
        ):
            capture_case(client, kind, question, **extra)
    tiny = settings.model_copy(update={'evidence_token_budget': 1})
    with TestClient(create_app(tiny, model=model, embedder=ReplayEmbedder())) as client:
        capture_case(client, 'budget_failure', "What is Sam's birth year?")
    snapshot = public_record(snapshot)
    files = {'snapshot.json': (json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
             'research-evidence.json': (ROOT / 'docs/team-v2/research-evidence.json').read_bytes()}
    frozen = output / 'bundle'
    frozen.mkdir()
    for name, content in files.items():
        (frozen / name).write_bytes(content)
    manifest = {'schema': 'public-console-replay-v1', 'mode': 'OFFLINE_SYNTHETIC_REPLAY', 'provider_calls': 0,
                'generator': 'tools/team_v2/freeze_demo.py',
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'quality_claim': 'none; controlled synthetic application cases, not model scores',
                'files': {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
    (frozen / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'bundle': str(frozen), 'cases': snapshot['cases'], 'provider_calls': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    requested = args.output.absolute()
    if any(path.is_symlink() for path in (requested, *requested.parents)):
        raise ValueError('output_symlink_forbidden')
    output = requested.resolve()
    output.relative_to((ROOT / 'var').resolve())
    output.mkdir(parents=True, exist_ok=False)
    export_fixture(output)
