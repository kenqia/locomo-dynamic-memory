"""Verify cached MiniLM indexing on an isolated accepted extraction snapshot."""
import argparse
import json
from pathlib import Path
import resource
import sqlite3
import time

import numpy as np

from locomo_memory.builds import BuildError, BuildService
from locomo_memory.config import Settings
from locomo_memory.database import Database
from locomo_memory.embeddings import MiniLMEmbedder
from locomo_memory.retrieval import RetrievalService
from locomo_memory.versions import VersionsService
from tools.m5.extraction_recovery import snapshot
from tools.m5.offline import sha, write


class NoProvider:
    def generate(self, *args, **kwargs):
        raise AssertionError('index_stage_must_not_call_provider')


def run(stage, output):
    stage, output = stage.resolve(), output.resolve()
    source = stage/'memory.sqlite3'
    original = snapshot(source)
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    target = output/'memory.sqlite3'
    # SQLite backup includes committed WAL. Source remains read-only.
    with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    target.chmod(0o600)
    # db_path is part of the frozen producer snapshot. Route storage through the
    # explicit Database object without rewriting that contract.
    settings = Settings.model_validate_json((stage/'settings.json').read_text())
    write(output/'settings.json', settings.model_dump(mode='json'))
    builds = BuildService(Database(target), settings, NoProvider())
    embedder = MiniLMEmbedder(settings)
    retrieval = RetrievalService(builds, settings, embedder, NoProvider())
    versions = VersionsService(builds)
    with builds.database.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT build_id,sample_id,status FROM build_versions ORDER BY sample_id')]
    results = []
    start, cpu = time.perf_counter(), time.process_time()
    for row in rows:
        if row['status'] == 'extracted':
            info = retrieval.create_index(row['build_id'])
            with builds.database.connect() as db:
                vectors = db.execute('SELECT COUNT(*),SUM(length(vector)) FROM index_entries WHERE build_id=?',
                                     (row['build_id'],)).fetchone()
                for entry in db.execute('SELECT vector FROM index_entries WHERE build_id=?', (row['build_id'],)):
                    vector = np.frombuffer(entry[0], dtype=np.float32)
                    assert vector.shape == (384,) and np.isfinite(vector).all()
                    assert np.isclose(np.linalg.norm(vector), 1, atol=1e-5)
            assert info['status'] == 'ready' and vectors[0] == info['memory_count']
            result = dict(sample_id=row['sample_id'], build_id=row['build_id'],
                status='indexed', memory_count=info['memory_count'], index_fingerprint=info['fingerprint'],
                embedding=info['embedding'], vector_bytes=vectors[1])
            try:
                versions.pin(builds.get(row['build_id'])['dataset_id'], row['sample_id'], row['build_id'])
            except BuildError as error:
                assert error.code == 'no_complete_version'
                result['query_pin_rejection'] = error.code
            else:
                raise AssertionError('incomplete_build_queryable')
        else:
            try:
                retrieval.create_index(row['build_id'])
            except BuildError as error:
                assert error.code == 'build_not_indexable'
                result = dict(sample_id=row['sample_id'], build_id=row['build_id'],
                    status=row['status'], index_rejection=error.code)
            else:
                raise AssertionError('failed_extraction_indexed')
        results.append(result)
    assert snapshot(source) == original
    summary = dict(status='local_index_verification_finished', builds=results,
        provider_requests=0, holdout_qa_read=False, original_database_unchanged=True,
        original_logical_snapshot=original, copied_database_sha256=sha(target),
        source_settings_sha256=sha(stage/'settings.json'), settings_sha256=sha(output/'settings.json'),
        storage_database=str(target), frozen_config_database=str(settings.db_path),
        wall_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, gpu_used=False,
        scope='Real cached local MiniLM, index only; no relation, publish, query or QA; no complete export claimed')
    write(output/'summary.json', summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.stage, args.output)
