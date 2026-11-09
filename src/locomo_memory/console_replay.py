"""Static read-only adapter for reviewed public synthetic fixture files."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote

import httpx

from locomo_memory.memory_schemas import Memory
from locomo_memory.relation_schemas import MemoryRelation
from locomo_memory.schemas import SourceTurn


class ReplayStore:
    def __init__(self, directory):
        directory = Path(directory)
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('mode') != 'OFFLINE_SYNTHETIC_REPLAY' or manifest.get('provider_calls') != 0:
            raise ValueError('synthetic_replay_required')
        for name in ('snapshot.json', 'research-evidence.json'):
            if hashlib.sha256((directory / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != manifest['files'].get(name):
                raise ValueError('replay_checksum_mismatch')
        self.data = json.loads((directory / 'snapshot.json').read_text(encoding='utf-8'))
        if self.data.get('schema') != 'public-console-replay-v1' or self.data.get('mode') != manifest['mode']:
            raise ValueError('replay_schema_mismatch')
        self.evidence_path = directory / 'research-evidence.json'
        self.cases = self.data['cases']
        source_ids = set()
        for source in self.data['sources']:
            SourceTurn.model_validate(source)
            if source['source_id'] != f"{source['dataset_id']}/{source['sample_id']}/{source['dia_id']}":
                raise ValueError('replay_source_identity_mismatch')
            source_ids.add(source['source_id'])
        for build in self.data['builds']:
            memories = self.data['memories'][build['build_id']]
            memory_ids = {m['memory_id'] for m in memories}
            for memory in memories:
                Memory.model_validate(memory)
                if ((memory['build_id'], memory['dataset_id'], memory['sample_id']) !=
                        (build['build_id'], build['dataset_id'], build['sample_id']) or
                        not set(memory['source_ids']) <= source_ids):
                    raise ValueError('replay_memory_scope_mismatch')
            for relation in self.data['relations'][build['build_id']]:
                MemoryRelation.model_validate(relation)
                if not {relation['old_memory_id'], relation['new_memory_id']} <= memory_ids:
                    raise ValueError('replay_relation_scope_mismatch')
        builds = {b['build_id']: b for b in self.data['builds']}
        for trace in self.data['traces'].values():
            build = builds[trace['build_id']]
            if (trace['dataset_id'], trace['sample_id']) != (build['dataset_id'], build['sample_id']):
                raise ValueError('replay_trace_scope_mismatch')

    def request(self, method, path, **kwargs):
        if method != 'GET':
            raise ValueError('replay_read_only')
        params = kwargs.get('params', {})
        parts = [unquote(part) for part in path.strip('/').split('/')]

        def page(items):
            limit, offset = int(params.get('limit', 20)), int(params.get('offset', 0))
            if not 1 <= limit <= 100 or offset < 0:
                raise ValueError('invalid_replay_page')
            return {'items': deepcopy(items[offset:offset + limit]), 'total': len(items), 'limit': limit, 'offset': offset}

        if parts == ['health']:
            return {'status': 'ok', 'mode': 'REPLAY'}
        if parts == ['datasets']:
            return page(self.data['datasets'])
        if parts == ['builds']:
            return page([b for b in self.data['builds'] if all(not params.get(k) or b[k] == params[k]
                         for k in ('dataset_id', 'sample_id'))])
        if parts == ['evaluation-runs']:
            return page(self.data['runs'])
        if len(parts) == 2 and parts[0] == 'queries' and parts[1] in self.data['traces']:
            return deepcopy(self.data['traces'][parts[1]])
        if len(parts) == 3 and parts[0] == 'builds':
            collection = {'memories': 'memories', 'relations': 'relations', 'current-state': 'projections'}.get(parts[2])
            if collection and parts[1] in self.data[collection]:
                value = self.data[collection][parts[1]]
                return deepcopy(value) if collection == 'projections' else page(value)
        known_dataset = len(parts) > 1 and any(d['dataset_id'] == parts[1] for d in self.data['datasets'])
        if known_dataset and parts[0] == 'datasets':
            if len(parts) == 3 and parts[2] == 'conversations':
                return page(self.data['conversations'])
            if len(parts) == 6 and parts[2] == 'conversations' and parts[4] == 'turns':
                source = next((s for s in self.data['sources'] if
                               (s['dataset_id'], s['sample_id'], s['dia_id']) == (parts[1], parts[3], parts[5])), None)
                if source:
                    return deepcopy(source)
        request = httpx.Request('GET', 'http://replay.local/' + path.lstrip('/'))
        raise httpx.HTTPStatusError('replay_resource_not_found', request=request,
                                    response=httpx.Response(404, request=request))
