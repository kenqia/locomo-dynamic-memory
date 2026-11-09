"""Pending review and new severe errors must block a semantic benefit claim."""
import importlib.util
import hashlib
import json
from pathlib import Path
import pytest
from locomo_memory.experiment import write_json

SCRIPT=Path(__file__).resolve().parents[1]/'experiments/dynamic-validation/score_review.py'
spec=importlib.util.spec_from_file_location('dynamic_review_scoring',SCRIPT)
scoring=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring)


def packet(tmp_path):
    original=[]
    key={}
    refs=[]
    for sid in ('x','y','z'):
        qid=f'{sid}:dynamic:01'
        refs.append(dict(question_id=qid,sample_id=sid,episode_id=f'{sid}:episode'))
        for arm in 'ABCDE':
            for repeat in (1,2,3):
                rid=f'{sid}{arm}{repeat}'
                key[rid]=f'{qid}:{repeat}:{arm}'
                original.append(dict(review_id=rid, question_id=qid, outcome='succeeded',answer=dict(answer='saved'),review={}))
    questions=[dict(question_id=ref['question_id'], groups=['dynamic'], dynamic_reference=ref) for ref in refs]
    write_json(tmp_path/'questions.json', questions)
    write_json(tmp_path/'plan.json',dict(samples=['x','y','z'],selection_seed='fixed',
        questions_sha256=hashlib.sha256((tmp_path/'questions.json').read_bytes()).hexdigest(),
        independent_review=dict(reviewer='卓新烨')))
    (tmp_path/'plan.sha256').write_text(hashlib.sha256((tmp_path/'plan.json').read_bytes()).hexdigest()+'\n')
    write_json(tmp_path/'review/blinded-answers.json',original)
    write_json(tmp_path/'analysis-private/review-key.json',key)
    write_json(tmp_path/'review/references-author-draft.json',refs)
    return original


def test_pending_review_does_not_become_zero_or_a_positive_claim(tmp_path):
    original=packet(tmp_path)
    path=tmp_path/'judgments.json'
    write_json(path,original)
    result=scoring.score(tmp_path,path)
    assert result['contrasts'][0]['equal_conversation_difference'] is None
    assert result['contrasts'][0]['primary_local_benefit_supported'] is None
    assert all(m['primary_complete_correct_rate'] is None for m in result['metrics'])
    original[0]['answer']['answer']='changed'
    write_json(path,original)
    with pytest.raises(ValueError,match='blinded_answer_changed'):
        scoring.score(tmp_path,path)


@pytest.mark.parametrize('new_severe',[False,True])
def test_paired_cluster_effect_is_reproducible_and_severe_error_blocks_claim(tmp_path,new_severe):
    original=packet(tmp_path)
    for r in original:
        severe=new_severe and r['review_id']=='xD1'
        r['review']=dict(reviewer='卓新烨',independently_reviewed=True,reference_accepted=True,
            complete_correct='D' in r['review_id'] and not severe,partial_correct=False,
            severe_temporal_state_error=severe,over_abstention=False)
    path=tmp_path/'judgments.json'
    write_json(path,original)
    result=scoring.score(tmp_path,path)
    assert result==scoring.score(tmp_path,path)
    main=result['contrasts'][0]
    assert main['equal_conversation_difference']>0
    assert main['descriptive_95_percentile_interval'][0]>0
    assert main['primary_local_benefit_supported'] is (not new_severe)


@pytest.mark.parametrize('damage', ['duplicate_repeat', 'missing_key', 'extra_key',
    'unknown_arm', 'unknown_question', 'changed_question', 'duplicate_reference',
    'duplicate_original', 'unknown_outcome', 'unsupported_design'])
def test_invalid_pair_identity_is_rejected_before_scoring(tmp_path, damage):
    original = packet(tmp_path)
    key_path = tmp_path / 'analysis-private/review-key.json'
    keys = json.loads(key_path.read_text())
    if damage == 'duplicate_repeat': keys['xD2'] = keys['xD1']
    if damage == 'missing_key': del keys['xD2']
    if damage == 'extra_key': keys['extra'] = 'x:dynamic:01:1:D'
    if damage == 'unknown_arm': keys['xD2'] = 'x:dynamic:01:2:Z'
    if damage == 'unknown_question': keys['xD2'] = 'absent:dynamic:01:2:D'
    if damage == 'changed_question': original[0]['question_id'] = 'y:dynamic:01'
    if damage == 'unknown_outcome': original[0]['outcome'] = 'invalid'
    if damage == 'duplicate_original': original.append(original[0])
    if damage == 'duplicate_reference':
        path = tmp_path / 'review/references-author-draft.json'
        refs = json.loads(path.read_text()); refs.append(refs[0]); write_json(path, refs)
    if damage == 'unsupported_design':
        path = tmp_path / 'plan.json'
        plan = json.loads(path.read_text()); plan['repeats'] = 2; write_json(path, plan)
    write_json(key_path, keys)
    write_json(tmp_path / 'review/blinded-answers.json', original)
    for row in original:
        row['review'] = dict(reviewer='卓新烨', independently_reviewed=True, reference_accepted=True,
            complete_correct='D' in row['review_id'], partial_correct=False,
            severe_temporal_state_error=False, over_abstention=False)
    path = tmp_path / 'judgments.json'; write_json(path, original)
    with pytest.raises(ValueError):
        scoring.score(tmp_path, path)
    assert not (tmp_path / 'independent-review-results.json').exists()


def test_unattempted_repetition_keeps_primary_comparison_incomplete(tmp_path):
    original = packet(tmp_path)
    original = [row for row in original if row['review_id'] != 'xD3']
    key_path = tmp_path / 'analysis-private/review-key.json'
    keys = json.loads(key_path.read_text()); del keys['xD3']; write_json(key_path, keys)
    write_json(tmp_path / 'review/blinded-answers.json', original)
    for row in original:
        row['review'] = dict(reviewer='卓新烨', independently_reviewed=True, reference_accepted=True,
            complete_correct='D' in row['review_id'], partial_correct=False,
            severe_temporal_state_error=False, over_abstention=False)
    path = tmp_path / 'judgments.json'; write_json(path, original)
    result = scoring.score(tmp_path, path)
    group = next(m for m in result['metrics'] if m['sample_id'] == 'x' and m['arm'] == 'D')
    assert group['pending_items'] == 1
    assert group['primary_complete_correct_rate'] is None
    assert result['contrasts'][0]['primary_local_benefit_supported'] is None


def test_failed_answer_retains_zero_score_without_semantic_error_judgments(tmp_path):
    original = packet(tmp_path)
    original[0]['outcome'] = 'failed'
    write_json(tmp_path / 'review/blinded-answers.json', original)
    original[0]['review'] = dict(reviewer='卓新烨', independently_reviewed=True, reference_accepted=True,
        complete_correct=False, partial_correct=False, severe_temporal_state_error=True, over_abstention=True)
    path = tmp_path / 'judgments.json'; write_json(path, original)
    result = scoring.score(tmp_path, path)
    group = next(m for m in result['metrics'] if m['sample_id'] == 'x' and m['arm'] == 'A')
    assert group['known_scored_items'] == group['failed_items'] == 1
    assert group['known_subset_correct_rate'] == 0
    assert group['severe_errors'] == group['over_abstentions'] == 0


@pytest.mark.parametrize('outcome', ['unknown', 'interrupted', 'running', 'pending'])
def test_saved_unresolved_outcomes_stay_visible_and_unscored(tmp_path, outcome):
    original = packet(tmp_path)
    original[0]['outcome'] = outcome
    write_json(tmp_path / 'review/blinded-answers.json', original)
    path = tmp_path / 'judgments.json'; write_json(path, original)
    result = scoring.score(tmp_path, path)
    group = next(m for m in result['metrics'] if m['sample_id'] == 'x' and m['arm'] == 'A')
    assert group['saved_outcomes'][outcome] == 1
    assert group['failed_items'] == 0
    assert group['known_scored_items'] == 0
    assert group['primary_complete_correct_rate'] is None


def test_changed_review_requires_a_new_output_and_preserves_prior_result(tmp_path):
    original = packet(tmp_path)
    path = tmp_path / 'judgments.json'; write_json(path, original)
    scoring.score(tmp_path, path)
    output = tmp_path / 'independent-review-results.json'
    before = output.read_bytes()
    original[0]['review']['rationale'] = 'New evidence for this review version'
    write_json(path, original)
    with pytest.raises(FileExistsError, match='choose a new --output'):
        scoring.score(tmp_path, path)
    assert output.read_bytes() == before
    alternative = tmp_path / 'review-v2.json'
    result = scoring.score(tmp_path, path, alternative)
    assert alternative.exists() and result['review_file_sha256']
    assert output.read_bytes() == before
