"""Prepare official development plans through existing APIs, without generation.

Run from the research worktree with PYTHONPATH=src and the existing Python env.
The database is dedicated to this experiment. No historical database is opened.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time
import sqlite3

import httpx
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings
from locomo_memory.experiment import Experiment, write_json
from locomo_memory.implementation_identity import implementation_sha256
from locomo_memory.imports import canonical_json
from locomo_memory.model import DeepSeekModel

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_HEAD = '915fac02f6b9296e331f913a1e78717cfa7e2df1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def combinations(plan):
    """Keep the application's question-major ordering and logical identity."""
    for question in plan['questions']:
        for strategy in plan['strategies']:
            yield {**{key: question[key] for key in ('sample_id', 'qa_index', 'question_id', 'category')},
                   'strategy': strategy, 'plan_id': plan['plan_id'],
                   'status': 'pending', 'build_id': None, 'run_id': None}


def prepare(directory, verify_embedding=False):
    directory = directory.resolve()
    if directory == ROOT or directory.is_relative_to(ROOT / 'data') or (directory / '.git').exists():
        raise ValueError('Choose a dedicated experiment directory')
    # Refuse before create_app/lifespan: startup recovery can mutate existing Runs.
    state_path = directory / 'experiment.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if state.get('builds') or state.get('smoke_run_id') or state.get('development_run_id') or state.get('pending_initiation'):
        raise ValueError('Preparation cannot overwrite an already started experiment')
    db_path = directory / 'memory.sqlite3'
    if db_path.exists():
        with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('build_versions', 'evaluation_runs'):
                if table in tables and db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:
                    raise ValueError('Preparation cannot overwrite an already started experiment')
    settings = Settings(db_path=directory / 'memory.sqlite3')
    attempted = []

    def deny_generation(request):
        attempted.append(True)
        raise AssertionError('Offline preparation must never send provider HTTP')

    # The real adapter and real MiniLM are retained; only generation HTTP is denied.
    model = DeepSeekModel(settings, transport=httpx.MockTransport(deny_generation))
    with TestClient(create_app(settings, model=model)) as client:
        experiment = Experiment(client, directory)
        experiment.prepare()
        tick = time.perf_counter()
        embedding = experiment.verify() if verify_embedding else experiment.preflight()
        embedding_check_seconds = time.perf_counter() - tick
        plans = {scope: json.loads((directory / f'plan-{scope}.json').read_text())
                 for scope in ('smoke', 'development')}
        # First API responses and persisted JSON can have different key order.
        # Canonicalize research exports so equivalent plans retain file hashes.
        for scope, saved_plan in plans.items():
            write_json(directory / f'plan-{scope}.json', json.loads(canonical_json(saved_plan)))
        plan = plans['development']
        assert plan['question_count'] == 757 and plan['combination_count'] == 3028
        assert plans['smoke']['combination_count'] == 20
        assert [q['qa_index'] for q in plans['smoke']['questions']] == [0, 2, 3, 82, 152]
        assert not attempted and client.get('/builds').json()['total'] == 0
        inputs = client.get('/evaluation-inputs/' + plan['input_id']).json()
        assert 'samples' in inputs, inputs
        write_json(directory / 'evaluation-input-development.json', inputs)
        source_summary = {}
        for sample_id in plan['course_split']['dev']:
            turns = experiment.page(f"/datasets/{plan['dataset_id']}/conversations/{sample_id}/turns")
            assert all(not ({'answer', 'evidence', 'qa'} & set(turn)) for turn in turns)
            write_json(directory / 'sources' / f'{sample_id}.json', turns)
            source_summary[sample_id] = {
                'turns': len(turns), 'text_turns': sum(bool(t.get('text')) for t in turns),
                'source_sha256': digest(directory / 'sources' / f'{sample_id}.json'),
                'question_count': sum(q['sample_id'] == sample_id for q in plan['questions']),
                'categories': dict(Counter(str(q['category']) for q in plan['questions'] if q['sample_id'] == sample_id)),
            }
    manifest = []
    for ordinal, row in enumerate(combinations(plan)):
        manifest.append({**row, 'ordinal': ordinal})
    path = directory / 'logical-combinations.jsonl'
    path.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in manifest))
    frozen = {
        'status': 'prepared_not_executed', 'production_head': PRODUCTION_HEAD,
        'research_head_at_preparation': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'implementation_sha256': implementation_sha256(), 'config': settings.snapshot(),
        'source_identity': {k: plan[k] for k in ('dataset_id', 'artifact_sha256', 'source_sha256', 'version', 'license', 'provenance')},
        'plan_ids': {k: p['plan_id'] for k, p in plans.items()},
        'plan_file_sha256': {k: digest(directory / f'plan-{k}.json') for k in plans},
        'combination_manifest_sha256': digest(path), 'question_count': 757, 'combination_count': len(manifest),
        'strategies': plan['strategies'], 'conversations': source_summary,
        'build_pins': {s: None for s in plan['course_split']['dev']}, 'run_ids': {'smoke': None, 'development': None},
        'model_http_calls': len(attempted), 'paid_authorization': None,
        'embedding_verification': embedding['embedding'],
        'embedding_verification_elapsed_seconds': embedding_check_seconds if verify_embedding else None,
        'scorer_sha256': digest(ROOT / 'src/locomo_memory/evaluation_metrics.py'),
        'identity_files': {str(p.relative_to(ROOT)): digest(p) for p in [
            ROOT / 'uv.lock', ROOT / 'pyproject.toml', ROOT / 'src/locomo_memory/model.py',
            ROOT / 'src/locomo_memory/memory_schemas.py', ROOT / 'src/locomo_memory/query_schemas.py',
            ROOT / 'src/locomo_memory/evaluation_execution.py']},
        'research_tool_files': {str(p.relative_to(ROOT)): digest(p)
                                for p in sorted((ROOT / 'tools/research_v2').glob('*.py'))},
        'limitations': ['BuildVersion pins and Run IDs are unset until authorized execution.',
                         'Preparation uses a generation-denying transport; it is not live smoke proof.',
                         'Only development questions and source turns are exported; evaluation answers stay in the isolated evaluator input.',
                         'Execution identity must be rechecked before starting or resuming.'],
    }
    write_json(directory / 'readiness.json', frozen)
    return frozen


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--verify-embedding', action='store_true', help='Load cached MiniLM locally; never download')
    args = parser.parse_args()
    record = prepare(args.directory, args.verify_embedding)
    print(json.dumps({k: record[k] for k in ('status', 'question_count', 'combination_count', 'model_http_calls', 'embedding_verification')}, indent=2))
