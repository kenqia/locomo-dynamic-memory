import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import httpx
from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.relation_schemas import RelationBatch

BASE = 'd65e380bc949497f8f095dfea1ed0062beacabd4'
def original_module(name, path):
    module = types.ModuleType('locomo_memory.' + name)
    sys.modules[module.__name__] = module
    source = subprocess.run(['git', 'show', BASE + ':' + path], check=True, capture_output=True, text=True).stdout
    exec(compile(source, path, 'exec'), module.__dict__)
    return module

old_model = original_module('_baseline_model', 'src/locomo_memory/model.py')
old_schema = original_module('_baseline_relations', 'src/locomo_memory/relation_schemas.py')
assert old_schema.RelationBatch.model_json_schema() == RelationBatch.model_json_schema()
settings = Settings(model_retries=2)
output = {'judgments': []}
def completion(content=json.dumps(output), finish='stop'):
    return {'choices': [{'finish_reason': finish, 'message': {'content': content}}],
            'usage': {'prompt_tokens': 3, 'completion_tokens': 1, 'total_tokens': 4}}

cases = {
    'success': [completion()],
    'json': [completion('{synthetic-private')],
    'schema': [completion('{}')],
    'enum': [completion(json.dumps({'judgments': [{'old_memory_id': 'old', 'new_memory_id': 'new', 'label': 'bad', 'reason': 'unknown', 'source_ids': ['s']}]}))],
    'domain': [completion(json.dumps({'judgments': [{'old_memory_id': 'old', 'new_memory_id': 'new', 'label': 'undetermined', 'reason': ' ', 'source_ids': ['s']}]}))],
    'length': [completion(finish='length')],
    'missing_finish': [completion(finish=None)],
    'empty': [completion(' ')],
    'malformed': [[]],
    'http': ['http'],
    'timeout': ['timeout'],
    'context_limit': ['context'],
    'failure_then_success': [completion('{synthetic-private'), completion()],
}
report = {'baseline': BASE, 'new_live_calls': 0, 'schema_equal': True, 'cases': []}
for name, responses in cases.items():
    runs = []
    for model_class, schema_class, failure_class in [(old_model.DeepSeekModel, old_schema.RelationBatch, old_model.ModelFailure), (DeepSeekModel, RelationBatch, ModelFailure)]:
        requests = []
        def provider(request):
            requests.append(request.content)
            response = responses[min(len(requests) - 1, len(responses) - 1)]
            if response == 'timeout':
                raise httpx.ReadTimeout('synthetic-private')
            if response == 'http':
                return httpx.Response(503, text='synthetic-private')
            if response == 'context':
                return httpx.Response(400, json={'error': {'code': 'context_length_exceeded'}})
            return httpx.Response(200, json=response)
        model = model_class(settings, api_key='synthetic', transport=httpx.MockTransport(provider))
        try:
            result = model.generate('relate', {'diagnostic_fixture': 'synthetic'}, schema_class)
            status, metadata = 'succeeded', result.metadata
        except failure_class as error:
            status, metadata = error.code, error.metadata
        runs.append((requests, status, [(call['outcome'], call['usage']) for call in metadata['calls']]))
    assert runs[0] == runs[1], name
    report['cases'].append({'case': name, 'equivalent': True, 'provider_attempts': len(runs[0][0]), 'outcome': runs[0][1], 'request_sha256': hashlib.sha256(runs[0][0][0]).hexdigest()})
Path('experiments/issue-15-diagnostics-contract-check.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'schema_equal': True, 'equivalent_cases': len(cases), 'mock_provider_calls_per_implementation': sum(item['provider_attempts'] for item in report['cases']), 'frozen_request_sha256': report['cases'][0]['request_sha256'], 'new_live_calls': 0}))
