"""Run application inspection/export against a disposable historical database copy."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory import builds, relation_diagnostics

# Match the startup-recovery clock in both processes. Otherwise the original
# unchanged recovery code creates distinct recovered_at values in the copies.
builds.utc_now = relation_diagnostics.utc_now = lambda: '2026-10-31T00:00:00+00:00'


class NoGeneration:
    def generate(self, *args, **kwargs):
        raise AssertionError('historical_read_smoke_must_not_generate')


path, output = map(Path, sys.argv[1:])
with sqlite3.connect(path) as connection:
    ids = [row[0] for row in connection.execute('SELECT build_id FROM build_versions ORDER BY build_id')]
results = []


def leaf_hashes(value, prefix='$'):
    if isinstance(value, dict):
        return {path: digest for key, child in value.items()
                for path, digest in leaf_hashes(child, prefix + '.' + key).items()}
    if isinstance(value, list):
        return {path: digest for index, child in enumerate(value)
                for path, digest in leaf_hashes(child, prefix + '[' + str(index) + ']').items()}
    return {prefix: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()}


with TestClient(create_app(Settings(db_path=path), model=NoGeneration(), embedder=object()), raise_server_exceptions=False) as client:
    assert client.get('/health').json() == {'status': 'ok'}
    for bid in ids:
        for endpoint in ('', '/memories?limit=100', '/current-state', '/export'):
            response = client.get('/builds/' + bid + endpoint)
            body = response.json()
            digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            results.append(dict(build_id=bid, endpoint=endpoint, status=response.status_code, json_sha256=digest,
                                error_code=body.get('error', {}).get('code'),
                                field_hashes=leaf_hashes(body) if endpoint == '' else {}))
with output.open('x') as stream:
    json.dump(results, stream, indent=2)
    stream.write('\n')
