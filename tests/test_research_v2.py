"""Offline research boundaries: missing evidence, retries, scope and provenance."""
import copy
import hashlib
import json

import pytest

from tools.research_v2.atlas import make_atlas
from tools.research_v2.prepare import combinations


def exported_run(tmp_path):
    def result(score):
        return {'qa': {'value': score}, 'source_coverage': {'initial': 1, 'answer_context': .5},
                'source_sets': {'answer_context': ['s1', 's1']},
                'trace': {'initial': {'channels': {'bm25': [], 'dense': [], 'rrf': []}},
                          'effective_memories': [], 'answer': {'answer': 'synthetic test answer', 'citations': []},
                          'operations': {'answer': {'calls': [{'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120}}]}}}}
    a = result(.2)
    b = result(1)
    items = []
    for n, (status, r) in enumerate([('succeeded', a), ('failed', None), ('unknown', None), ('succeeded', b)]):
        attempts = [{'status': status, 'result': r, 'elapsed_seconds': None}]
        if n == 0:
            attempts.insert(0, {'status': 'unknown', 'result': None})
        items.append({'ordinal': n, 'question_id': f'conv-26:qa:{n}', 'qa_index': n,
                      'sample_id': 'conv-26', 'sample_index': n, 'strategy': 'dynamic',
                      'status': status, 'attempts': attempts, 'result': r})
    run = {'run_id': 'synthetic-test-only', 'pins': {'conv-26': 'b1'}, 'items': items,
           'builds': {'conv-26': {'build_id': 'b1'}},
           'input': {'samples': [{'category': 1}] * 4}}
    path = tmp_path / 'run.json'
    path.write_text(json.dumps(run))
    return run, path


def test_failed_scores_and_retrieval_hits_never_establish_root_cause(tmp_path):
    run, path = exported_run(tmp_path)
    cases, summary = make_atlas(run, path, tmp_path)
    assert len(cases) == 3
    assert summary['logical_denominator'] == 4
    assert summary['all_items']['states'] == {'succeeded': 2, 'failed': 1, 'unknown': 1}
    assert summary['groups']['failure_type']['Unknown']['planned'] == 3
    assert all(c['diagnosis']['type'] == 'Unknown' for c in cases)
    assert summary['top_10_confirmed_patterns'] == []
    assert cases[0]['lineage']['original_source_turns']['status'] == 'missing'
    assert cases[0]['lineage']['actual_model_context']['status'] == 'exact_wire_not_recorded'
    assert cases[0]['lineage']['cost_and_trace']['cost']['known_prompt_tokens'] == 100
    assert cases[0]['lineage']['cost_and_trace']['cost']['complete_usage_peak_cny_estimate'] is None
    assert summary['all_items']['citation_correctness']['value'] is None
    assert summary['all_items']['severe_error_ratio']['value'] is None


def test_retry_cost_retains_failed_attempt_and_unknown_fields(tmp_path):
    run, path = exported_run(tmp_path)
    item = run['items'][0]
    first_result = copy.deepcopy(item['result'])
    item['attempts'][0] = {'status': 'failed', 'result': first_result, 'elapsed_seconds': 1}
    cases, _ = make_atlas(run, path, tmp_path)
    cost = cases[0]['lineage']['cost_and_trace']['cost']
    assert cost['logical_retries'] == 1
    assert cost['known_prompt_tokens'] == 200
    assert cost['saved_physical_calls'] == 2
    assert cost['complete_usage_peak_cny_estimate'] == pytest.approx(.00072)
    del first_result['trace']['operations']['answer']['calls'][0]['usage']['completion_tokens']
    cases, _ = make_atlas(run, path, tmp_path)
    assert cases[0]['lineage']['cost_and_trace']['cost']['complete_usage_peak_cny_estimate'] is None


@pytest.mark.parametrize('mutation', ['test_conversation', 'extra_strategy', 'duplicate'])
def test_atlas_refuses_test_scope_and_spliced_logical_items(tmp_path, mutation):
    run, path = exported_run(tmp_path)
    if mutation == 'test_conversation':
        run['items'][0]['sample_id'] = 'conv-43'
    elif mutation == 'extra_strategy':
        run['items'][0]['strategy'] = 'dynamic_raw_fallback'
    else:
        run['items'].append(copy.deepcopy(run['items'][0]))
    with pytest.raises(ValueError):
        make_atlas(run, path, tmp_path)


def test_review_requires_existing_hashed_stage_evidence_and_independence(tmp_path):
    run, path = exported_run(tmp_path)
    review = {'case_id': 'synthetic-test-only:0', 'type': 'Reasoning Failure',
              'reviewer': 'independent synthetic test reviewer', 'independent': True,
              'reason': 'Synthetic test declaration only', 'pattern': 'synthetic pattern',
              'severe': False, 'citation_correctness': .5,
              'evidence': [{'path': 'run.json', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'pointer': '/items/0/result/trace/answer'}]}
    cases, summary = make_atlas(run, path, tmp_path, [review])
    assert cases[0]['diagnosis']['type'] == 'Reasoning Failure'
    assert summary['top_10_confirmed_patterns'] == [{'pattern': 'synthetic pattern', 'cases': 1}]
    review['independent'] = False
    with pytest.raises(ValueError):
        make_atlas(run, path, tmp_path, [review])
    review['independent'] = True
    review['evidence'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        make_atlas(run, path, tmp_path, [review])


def test_full_text_delivery_is_not_reported_as_retrieval_ability(tmp_path):
    run, path = exported_run(tmp_path)
    for item in run['items']:
        item['strategy'] = 'full_text'
    _, summary = make_atlas(run, path, tmp_path)
    assert summary['all_items']['initial_retrieval_coverage']['value'] is None
    assert summary['all_items']['full_text_input_coverage']['value'] == 1
    assert 'not_applicable' in summary['groups']['memory_source_count']


def test_combination_manifest_keeps_official_order_and_excludes_annotations():
    plan = {'plan_id': 'synthetic-test-plan', 'strategies': ['full_text', 'vector', 'hybrid_no_resolution', 'dynamic'],
            'questions': [{'sample_id': 'conv-26', 'qa_index': 82, 'question_id': 'conv-26:qa:82',
                           'category': 4, 'question': 'synthetic question', 'answer': 'must not leak', 'evidence': ['must not leak']}]}
    rows = list(combinations(plan))
    assert [r['strategy'] for r in rows] == plan['strategies']
    assert all(r['build_id'] is None and r['run_id'] is None for r in rows)
    assert all(not {'question', 'answer', 'evidence'} & set(r) for r in rows)


def test_offline_preparation_reuses_the_official_plan_and_refuses_started_runs(tmp_path):
    import sqlite3
    from tools.research_v2.prepare import prepare
    directory = tmp_path / 'research'
    first = prepare(directory)
    second = prepare(directory)
    assert first['plan_ids'] == second['plan_ids']
    assert first['plan_file_sha256'] == second['plan_file_sha256']
    assert first['combination_manifest_sha256'] == second['combination_manifest_sha256']
    rows = [json.loads(line) for line in (directory / 'logical-combinations.jsonl').read_text().splitlines()]
    assert len(rows) == 3028
    assert all(row['status'] == 'pending' and row['run_id'] is None for row in rows)
    state_path = directory / 'experiment.json'
    state = json.loads(state_path.read_text())
    state['smoke_run_id'] = 'synthetic-started-run'
    state_path.write_text(json.dumps(state))
    before = state_path.read_bytes()
    with pytest.raises(ValueError, match='already started'):
        prepare(directory)
    assert state_path.read_bytes() == before
    # A lost receipt must not let application startup recover/mutate an old Run.
    state['smoke_run_id'] = None
    state_path.write_text(json.dumps(state))
    with sqlite3.connect(directory / 'memory.sqlite3') as db:
        db.execute('INSERT INTO evaluation_runs VALUES (?,?)', ('synthetic-existing-run', '{}'))
    with pytest.raises(ValueError, match='already started'):
        prepare(directory)
    with sqlite3.connect(directory / 'memory.sqlite3') as db:
        assert db.execute('SELECT result_json FROM evaluation_runs').fetchone()[0] == '{}'
