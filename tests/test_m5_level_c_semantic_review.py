"""Semantic review contracts with a complete, synthetic 200-item freeze only."""
from contextlib import contextmanager
from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from locomo_memory.config import Settings
from tools.m5 import level_c
from tools.m5 import level_c_semantic_review as review
from tools.m5.offline import sha, write


def replace(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


@pytest.fixture
def frozen(tmp_path):
    """Build real frozen_items inputs without a model, extraction, or Gold reads."""
    stage = tmp_path/'generation'
    stage.mkdir()
    sources = {}
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        db.executescript('''
            CREATE TABLE conversations(dataset_id TEXT, sample_id TEXT, turn_count INTEGER);
            CREATE TABLE source_turns(source_id TEXT PRIMARY KEY, dataset_id TEXT,
                sample_id TEXT, session_id TEXT, dia_id TEXT, speaker TEXT,
                session_time TEXT, text TEXT, position INTEGER);
            CREATE TABLE evaluation_runs(secret TEXT);
            INSERT INTO evaluation_runs VALUES ('SYNTHETIC_GOLD_DO_NOT_READ');
        ''')
        # A holdout source exists only as a tripwire; it must never enter a packet.
        for conv in (*level_c.DEV, 'conv-43'):
            db.execute('INSERT INTO conversations VALUES (?,?,?)', ('synthetic', conv, 2))
            sources[conv] = [dict(source_id=f'synthetic/{conv}/D1:{i}', dataset_id='synthetic',
                sample_id=conv, session_id='session_1', dia_id=f'D1:{i}', speaker='Alex',
                session_time='10:00 am on 2 May, 2023',
                text=(f'{conv} Alex lives in Rome and plays chess.' if i == 1
                      else f'{conv} Alex moved from Paris to Rome on 2 May 2023.'), position=i-1)
                for i in (1, 2)]
            db.executemany('INSERT INTO source_turns VALUES (?,?,?,?,?,?,?,?,?)',
                           [tuple(source.values()) for source in sources[conv]])
    ordinary = [f'{conv}:qa:{i}' for conv in level_c.DEV for i in range(20)]
    diagnostic = [f'{conv}:qa:{i}' for conv in level_c.DEV for i in range(20, 25)]
    questions = [dict(question_id=qid, sample_id=qid.split(':qa:')[0],
                      question='Where does Alex live?',
                      stratum='ordinary' if qid in ordinary else 'diagnostic')
                 for qid in ordinary+diagnostic]
    settings = Settings(db_path=stage/'memory.sqlite3', model_max_tokens=32768, **level_c.V2_SETTINGS)
    write(stage/'settings.json', settings.snapshot())
    write(stage/'inputs.json', questions)
    write(stage/'sample.json', dict(ordinary=ordinary, diagnostic=diagnostic))
    write(stage/'build-identities.json', [])
    plan = dict(status='prepared_not_authorized', proposal_version=level_c.PROPOSAL_VERSION, scope=level_c.SCOPE,
                dataset_id='synthetic', pins={conv: f'synthetic-{conv}' for conv in level_c.DEV},
                arms=list(level_c.ARMS), questions=100, planned_items=200,
                strata=dict(ordinary=80, diagnostic=20),
                implementation_sha256=level_c.producer_hashes(),
                settings_sha256=sha(stage/'settings.json'), inputs_sha256=sha(stage/'inputs.json'),
                sample_sha256=sha(stage/'sample.json'),
                build_identities_sha256=sha(stage/'build-identities.json'),
                policy=level_c.policy_for(100, settings),
                gold_read=False, holdout_read=False, bonus_enabled=False)
    write(stage/'plan.json', plan)
    hashes = {}
    for index, question in enumerate(questions):
        for arm in level_c.ARMS:
            failed = question['question_id'].endswith(':qa:0') and arm == 'hybrid_no_resolution'
            answer = dict(status='sufficient', answer='Rome', explanation='Alex moved to Rome.',
                          citations=[dict(memory_id='opaque-memory',
                                          source_ids=[s['source_id'] for s in sources[question['sample_id']]])])
            item = dict(question_id=question['question_id'], sample_id=question['sample_id'],
                        stratum=question['stratum'], arm=arm,
                        outcome='failed' if failed else 'succeeded',
                        prediction=None if failed else 'Rome', error_code='PRIVATE_ERROR_TYPE',
                        trace=dict(answer=None if failed else answer, qa_score=.9,
                                   resolution=dict(decisions=['PRIVATE_RESOLVER_DECISION'])))
            name = f'items/{index:03d}-{arm}.json'
            write(stage/name, item)
            hashes[name] = sha(stage/name)
    write(stage/'generation-freeze.json', dict(status='generation_complete', planned_items=200,
          plan_sha256=sha(stage/'plan.json'), item_hashes=hashes))
    return stage, tmp_path/'private-review'


@pytest.fixture
def bundle(frozen):
    stage, output = frozen
    review.prepare(stage, output)
    return stage, output


def quote(source, targets, purpose='support'):
    return dict(source_id=source['source_id'], quote=source['text'],
                rationale='Synthetic source identifies Alex and the move.',
                purpose=purpose, targets=targets)


def complete_reviews(bundle):
    _, output = bundle
    packets = json.loads((output/'packets.json').read_text())
    document = json.loads((output/'review-template.json').read_text())
    units = {unit['unit_id']: unit for unit in packets['units']}
    for row in document['units']:
        unit = units[row['unit_id']]
        failed = unit['outcome'] == 'failed'
        row.update(reviewer='Independent synthetic reviewer',
                   provenance='Synthetic sources only; not involved in generation; all claims checked.',
                   review_kind='human_independent', independent_of_generation=True,
                   all_factual_claims_checked=True,
                   answer_kind='failed' if failed else 'answered',
                   source_support='not_applicable' if failed else 'supported',
                   citation_support='not_applicable' if failed else 'supported',
                   abstention='not_applicable', rationale='Synthetic failure.' if failed else 'All claims match the two supplied sources.',
                   full_conversation_checked=True, evidence_gap=None,
                   source_quotes=[] if failed else [quote(source, ['source_support', 'citation_support'])
                       for source in packets['conversations'][unit['conversation_id']]])
        row.update({key: None if failed else False for key in review.ERRORS})
    return document


def save_reviews(bundle, document):
    path = bundle[1]/'reviews.json'
    replace(path, document)
    return path


def success_row(document):
    return next(row for row in document['units'] if row['answer_kind'] == 'answered')


def test_prepare_blinds_all_200_shares_complete_sources_and_changes_no_stage_files(frozen, monkeypatch):
    stage, output = frozen
    before = {str(path.relative_to(stage)): sha(path) for path in stage.rglob('*') if path.is_file()}
    statements = []
    original_readonly = review.readonly

    @contextmanager
    def guarded(path):
        assert path == stage/'memory.sqlite3'
        with original_readonly(path) as db:
            def authorize(action, table, column, database, trigger):
                if action == sqlite3.SQLITE_READ:
                    assert table in ('conversations', 'source_turns')
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
            db.set_trace_callback(statements.append)
            yield db
    monkeypatch.setattr(review, 'readonly', guarded)
    result = review.prepare(stage, output)
    assert result == dict(planned=200, reviewed=0, unreviewed=200, completed=False,
                          gold_read=False, provider_calls=0)
    packets = json.loads((output/'packets.json').read_text())
    assert len(packets['units']) == 200
    assert set(packets['conversations']) == set(level_c.DEV)
    assert all(len(sources) == 2 for sources in packets['conversations'].values())
    assert Counter([unit['conversation_id'] for unit in packets['units']]) == {
        conv: 50 for conv in level_c.DEV}
    for unit in packets['units']:
        assert set(unit) == {'unit_id', 'conversation_id', 'question', 'outcome', 'prediction', 'answer'}
        if unit['answer']:
            assert set(unit['answer']) == {'status', 'answer', 'explanation', 'citations'}
    raw = (output/'packets.json').read_text()
    for hidden in ('PRIVATE_ERROR_TYPE', 'PRIVATE_RESOLVER_DECISION', 'qa_score',
                   'hybrid_no_resolution', 'dynamic', 'question_id', 'SYNTHETIC_GOLD', 'conv-43'):
        assert hidden not in raw
    assert all('conv-43' not in statement for statement in statements)
    assert all(row[field] is None for row in json.loads((output/'review-template.json').read_text())['units']
               for field in review.REVIEW_FIELDS)
    assert {str(path.relative_to(stage)): sha(path) for path in stage.rglob('*') if path.is_file()} == before
    assert output.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in output.iterdir())
    assert review.unit_id('conv-26:qa:1', 'dynamic') == review.unit_id('conv-26:qa:1', 'dynamic')
    assert review.unit_id('conv-26:qa:1', 'dynamic') != review.unit_id('conv-26:qa:1', 'hybrid_no_resolution')


def test_pending_template_is_unreviewed_and_never_final_score(bundle):
    stage, output = bundle
    result = review.validate(stage, output, output/'review-template.json')
    assert result['completed'] is False
    assert result['summary']['overall']['unreviewed'] == 200
    assert result['summary']['overall']['source_support']['denominator'] == 0
    assert result['summary']['overall']['source_support']['rate'] is None
    with pytest.raises(ValueError, match='all_200_independent_reviews'):
        review.score(stage, output, output/'review-template.json')


def test_complete_review_denominators_exclude_failures_and_unknown_without_text_leak(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    row.update(source_support='undetermined', citation_support='undetermined', source_quotes=[],
               **{key: None for key in review.ERRORS})
    result = review.score(*bundle, save_reviews(bundle, document))
    overall = result['summary']['overall']
    assert result['completed'] and overall['planned'] == overall['reviewed'] == 200
    assert overall['failed'] == 4 and overall['undetermined'] == 1
    for field in ('source_support', 'citation_support', *review.ERRORS):
        assert overall[field]['denominator'] == 195
    assert overall['source_support']['rate'] == 1
    assert overall['wrong_person']['rate'] == 0
    assert overall['wrong_person']['undetermined_or_not_applicable'] == 1
    assert overall['abstention']['denominator'] == 0 and overall['abstention']['rate'] is None
    for conv in level_c.DEV:
        assert result['summary']['by_conversation'][conv]['planned'] == 50
    assert result['summary']['by_stratum_arm']['ordinary/dynamic']['planned'] == 80
    assert result['summary']['by_stratum_arm']['diagnostic/dynamic']['planned'] == 20
    raw = json.dumps(result)
    for private in ('Where does Alex', 'Rome', 'Synthetic source', 'Independent synthetic reviewer', 'source_quotes'):
        assert private not in raw


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'outside'])
def test_exact_200_unique_review_identities_required(bundle, change):
    document = complete_reviews(bundle)
    if change == 'missing':
        document['units'].pop()
    elif change == 'duplicate':
        document['units'][0] = deepcopy(document['units'][1])
    else:
        document['units'][0]['unit_id'] = '0'*64
    with pytest.raises(ValueError, match='semantic_(all_200_review_units|review_unit_identity)_required'):
        review.validate(*bundle, save_reviews(bundle, document))


@pytest.mark.parametrize('field,value', [
    ('reviewer', ''), ('provenance', None), ('review_kind', 'model_generated'),
    ('independent_of_generation', False), ('all_factual_claims_checked', False),
])
def test_review_requires_independent_provenance_and_all_explanation_claims_attestation(bundle, field, value):
    document = complete_reviews(bundle)
    success_row(document)[field] = value
    with pytest.raises(ValueError, match='semantic_independent_review_required'):
        review.validate(*bundle, save_reviews(bundle, document))


@pytest.mark.parametrize('wrong', ['cross_conversation', 'nonverbatim', 'missing_rationale'])
def test_quote_identity_and_verbatim_check_are_conversation_scoped(bundle, wrong):
    document = complete_reviews(bundle)
    target = success_row(document)['source_quotes'][0]
    if wrong == 'cross_conversation':
        packets = json.loads((bundle[1]/'packets.json').read_text())
        other = next(sources[0] for sources in packets['conversations'].values()
                     if sources[0]['source_id'] != target['source_id'])
        target.update(source_id=other['source_id'], quote=other['text'])
    elif wrong == 'nonverbatim':
        target['quote'] = 'Alex lives in Berlin.'
    else:
        target['rationale'] = ''
    with pytest.raises(ValueError, match='semantic_(same_conversation_verbatim|quote_rationale_and_targets)_required'):
        review.validate(*bundle, save_reviews(bundle, document))


def test_actual_citations_need_complete_support_quotes_not_one_good_id(bundle):
    document = complete_reviews(bundle)
    success_row(document)['source_quotes'].pop()
    with pytest.raises(ValueError, match='semantic_complete_actual_citation_quotes_required'):
        review.validate(*bundle, save_reviews(bundle, document))


def test_source_support_does_not_imply_citation_support(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    for evidence in row['source_quotes']:
        evidence['targets'] = ['source_support']
    with pytest.raises(ValueError, match='semantic_supported_label_needs_quote'):
        review.validate(*bundle, save_reviews(bundle, document))


def test_uncited_source_cannot_be_claimed_as_supported_citation(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    # The source is valid in this conversation but the generation cites a missing ID.
    # Changing all upstream hashes still cannot turn that ID into source support.
    stage, output = bundle
    mapping = json.loads((output/'private-mapping.json').read_text())['units']
    identity = next(item for item in mapping if item['unit_id'] == row['unit_id'])
    inputs = json.loads((stage/'inputs.json').read_text())
    index = next(i for i, item in enumerate(inputs) if item['question_id'] == identity['question_id'])
    path = stage/f"items/{index:03d}-{identity['arm']}.json"
    item = json.loads(path.read_text())
    item['trace']['answer']['citations'][0]['source_ids'] = ['missing-source']
    replace(path, item)
    freeze = json.loads((stage/'generation-freeze.json').read_text())
    freeze['item_hashes'][str(path.relative_to(stage))] = sha(path)
    replace(stage/'generation-freeze.json', freeze)
    fresh = output.parent/'review-with-bad-citation'
    review.prepare(stage, fresh)
    new_bundle = (stage, fresh)
    document = complete_reviews(new_bundle)
    with pytest.raises(ValueError, match='semantic_complete_actual_citation_quotes_required'):
        review.score(*new_bundle, save_reviews(new_bundle, document))


def test_undetermined_kind_preserves_unknown_without_rates(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    row.update(answer_kind='undetermined', source_support='undetermined',
               citation_support='undetermined', abstention='undetermined', source_quotes=[],
               **{key: None for key in review.ERRORS})
    result = review.score(*bundle, save_reviews(bundle, document))
    overall = result['summary']['overall']
    assert overall['undetermined'] == 1
    assert overall['source_support']['undetermined'] == 1
    assert overall['source_support']['denominator'] == 195
    assert overall['abstention']['denominator'] == 0


def test_unsupported_can_use_gap_quote_without_fabricated_positive_evidence(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    row.update(source_support='unsupported', citation_support='unsupported')
    for evidence in row['source_quotes']:
        evidence.update(purpose='gap', rationale='The closest source states a move, not uninterrupted residency.')
    result = review.score(*bundle, save_reviews(bundle, document))
    assert result['summary']['overall']['source_support']['negative'] == 1
    assert result['summary']['overall']['source_support']['denominator'] == 196


def test_error_true_requires_targeted_counterevidence_quote(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    row['wrong_time'] = True
    with pytest.raises(ValueError, match='semantic_error_needs_quote'):
        review.validate(*bundle, save_reviews(bundle, document))
    evidence = deepcopy(row['source_quotes'][1])
    evidence.update(purpose='counterevidence', targets=['wrong_time'])
    row['source_quotes'].append(evidence)
    result = review.score(*bundle, save_reviews(bundle, document))
    assert result['summary']['overall']['wrong_time']['positive'] == 1
    assert result['summary']['overall']['wrong_time']['rate'] == 1/196


def test_correct_blanket_abstention_requires_full_conversation_gap_and_can_have_no_quote(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    row.update(answer_kind='abstained', source_support='not_applicable',
               citation_support='not_applicable', abstention='correct', source_quotes=[],
               full_conversation_checked=False,
               evidence_gap='Complete conversation describes residency, not an exact acquisition date.')
    with pytest.raises(ValueError, match='semantic_correct_abstention_needs_full_conversation_gap'):
        review.validate(*bundle, save_reviews(bundle, document))
    row['full_conversation_checked'] = True
    result = review.score(*bundle, save_reviews(bundle, document))
    assert result['summary']['overall']['abstention']['positive'] == 1
    assert result['summary']['overall']['abstention']['denominator'] == 1


def test_false_blanket_abstention_needs_verbatim_answerable_evidence(bundle):
    document = complete_reviews(bundle)
    row = success_row(document)
    row.update(answer_kind='abstained', source_support='not_applicable',
               citation_support='not_applicable', abstention='false')
    for evidence in row['source_quotes']:
        evidence['targets'] = ['source_support']
    with pytest.raises(ValueError, match='semantic_false_abstention_needs_quote'):
        review.validate(*bundle, save_reviews(bundle, document))
    row['source_quotes'][0]['targets'].append('abstention')
    result = review.score(*bundle, save_reviews(bundle, document))
    assert result['summary']['overall']['abstention']['negative'] == 1


@pytest.mark.parametrize('field,value', [('source_support', 'unsupported'), ('wrong_person', True), ('answer_kind', 'answered')])
def test_failed_generation_is_na_not_a_semantic_error(bundle, field, value):
    document = complete_reviews(bundle)
    row = next(row for row in document['units'] if row['answer_kind'] == 'failed')
    row[field] = value
    with pytest.raises(ValueError, match='semantic_failed_item_must_be_not_applicable'):
        review.validate(*bundle, save_reviews(bundle, document))


@pytest.mark.parametrize('artifact', ['packets.json', 'private-mapping.json', 'generation-freeze.json'])
def test_bound_hashes_must_not_change(bundle, artifact):
    stage, output = bundle
    document = complete_reviews(bundle)
    path = (stage if artifact == 'generation-freeze.json' else output)/artifact
    content = json.loads(path.read_text())
    content['tampered'] = True
    replace(path, content)
    with pytest.raises(ValueError, match='semantic_(packet_hash|mapping_hash|generation_binding)_changed'):
        review.validate(*bundle, save_reviews(bundle, document))


def test_rewriting_manifest_does_not_allow_a_changed_packet_projection(bundle):
    stage, output = bundle
    document = complete_reviews(bundle)
    packets = json.loads((output/'packets.json').read_text())
    packets['units'][0]['prediction'] = 'Tampered output'
    replace(output/'packets.json', packets)
    manifest = json.loads((output/'manifest.json').read_text())
    manifest['packets_sha256'] = sha(output/'packets.json')
    replace(output/'manifest.json', manifest)
    document['manifest_sha256'] = sha(output/'manifest.json')
    with pytest.raises(ValueError, match='semantic_packet_projection_changed'):
        review.validate(stage, output, save_reviews(bundle, document))


def test_rewriting_manifest_does_not_allow_mapping_reassignment(bundle):
    stage, output = bundle
    document = complete_reviews(bundle)
    mapping = json.loads((output/'private-mapping.json').read_text())
    mapping['units'][0]['arm'] = 'dynamic' if mapping['units'][0]['arm'] != 'dynamic' else 'hybrid_no_resolution'
    replace(output/'private-mapping.json', mapping)
    manifest = json.loads((output/'manifest.json').read_text())
    manifest['mapping_sha256'] = sha(output/'private-mapping.json')
    replace(output/'manifest.json', manifest)
    document['manifest_sha256'] = sha(output/'manifest.json')
    with pytest.raises(ValueError, match='semantic_mapping_identity_changed'):
        review.validate(stage, output, save_reviews(bundle, document))


def test_artifacts_changed_while_labels_are_checked_cannot_produce_summary(bundle, monkeypatch):
    document = complete_reviews(bundle)
    original = review.check_review
    changed = []

    def racing(unit, row, sources):
        original(unit, row, sources)
        if not changed:
            path = bundle[1]/'packets.json'
            path.write_text(path.read_text()+'\n')
            changed.append(True)
    monkeypatch.setattr(review, 'check_review', racing)
    with pytest.raises(ValueError, match='semantic_review_artifacts_changed_during_validation'):
        review.score(*bundle, save_reviews(bundle, document))


def test_review_manifest_hash_itself_is_bound(bundle):
    document = complete_reviews(bundle)
    document['manifest_sha256'] = '0'*64
    with pytest.raises(ValueError, match='semantic_review_manifest_binding_required'):
        review.validate(*bundle, save_reviews(bundle, document))


def test_generation_item_mutation_rejected_before_source_access(bundle, monkeypatch):
    stage, _ = bundle
    document = complete_reviews(bundle)
    path = next((stage/'items').iterdir())
    path.write_text('{}')
    monkeypatch.setattr(review, 'conversation_sources', lambda *args: pytest.fail('premature source open'))
    with pytest.raises(ValueError, match='generation_item_changed'):
        review.validate(*bundle, save_reviews(bundle, document))


def test_missing_or_incomplete_freeze_refuses_prepare_before_source_access(frozen, monkeypatch):
    stage, output = frozen
    path = stage/'generation-freeze.json'
    freeze = json.loads(path.read_text())
    path.rename(stage/'incomplete-original.json')
    monkeypatch.setattr(review, 'conversation_sources', lambda *args: pytest.fail('unfrozen source open'))
    with pytest.raises(FileNotFoundError):
        review.prepare(stage, output)
    freeze['item_hashes'].pop(next(iter(freeze['item_hashes'])))
    replace(path, freeze)
    with pytest.raises(ValueError, match='generation_not_completely_frozen'):
        review.prepare(stage, output)
    assert not output.exists()


def test_target_source_mutation_and_truncation_are_detected(bundle):
    stage, output = bundle
    document = complete_reviews(bundle)
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        db.execute("UPDATE source_turns SET text='Changed source' WHERE sample_id=?", (level_c.DEV[0],))
    with pytest.raises(ValueError, match='semantic_conversation_sources_changed'):
        review.validate(stage, output, save_reviews(bundle, document))
    with sqlite3.connect(stage/'memory.sqlite3') as db:
        db.execute('DELETE FROM source_turns WHERE sample_id=? AND position=0', (level_c.DEV[0],))
    with pytest.raises(ValueError, match='semantic_full_conversation_required'):
        review.prepare(stage, output.parent/'second-review')


def test_prepare_cannot_write_inside_generation_stage(frozen):
    stage, _ = frozen
    with pytest.raises(ValueError, match='semantic_output_must_be_outside_stage'):
        review.prepare(stage, stage/'forbidden-review')
