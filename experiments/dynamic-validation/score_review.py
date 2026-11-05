"""Score completed independent judgments without treating pending reviews as truth."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import statistics

PAIRS=(('D','A'),('B','A'),('D','C'),('C','A'),('D','B'),('D','E'))

def read(path):
    return json.loads(path.read_text())

def average(values):
    return statistics.mean(values) if values else None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_pair_identities(plan, original, key, references):
    """Check the saved five-arm design before counting rows as repetitions."""
    if (plan.get('repeats', 3) != 3 or set(plan.get('arms', 'ABCDE')) != set('ABCDE')
            or not plan['samples'] or len(set(plan['samples'])) != len(plan['samples'])):
        raise ValueError('unsupported_review_design')
    refs = {ref['question_id']: ref for ref in references}
    if len(refs) != len(references) or any(ref['sample_id'] not in plan['samples'] for ref in references):
        raise ValueError('invalid_reference_scope')
    ids = [row['review_id'] for row in original]
    if len(set(ids)) != len(ids) or set(ids) != set(key):
        raise ValueError('review_key_scope_mismatch')
    seen = set()
    for row in original:
        parts = key[row['review_id']].rsplit(':', 2)
        if len(parts) != 3:
            raise ValueError('invalid_paired_item_identity')
        qid, repeat, arm = parts
        identity = (qid, repeat, arm)
        if (qid not in refs or row['question_id'] != qid or repeat not in ('1', '2', '3')
                or arm not in 'ABCDE' or len(arm) != 1 or identity in seen):
            raise ValueError('invalid_or_duplicate_paired_item_identity')
        if row['outcome'] not in ('succeeded', 'failed', 'unknown', 'interrupted', 'pending', 'running'):
            raise ValueError('invalid_review_outcome')
        seen.add(identity)
    return refs


def score(directory, judgments, output=None):
    plan=read(directory/'plan.json')
    require(hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest()==
        (directory/'plan.sha256').read_text().strip(), 'frozen_plan_changed')
    require(hashlib.sha256((directory/'questions.json').read_bytes()).hexdigest()==
        plan['questions_sha256'], 'frozen_questions_changed')
    original=read(directory/'review/blinded-answers.json')
    key=read(directory/'analysis-private/review-key.json')
    references=read(directory/'review/references-author-draft.json')
    require(references==[q.get('dynamic_reference',q) for q in read(directory/'questions.json')
        if 'dynamic' in q['groups']], 'reference_scope_differs_from_frozen_questions')
    refs=validate_pair_identities(plan, original, key, references)
    source={r['review_id']:r for r in original}
    supplied=read(judgments)
    require(len({r['review_id'] for r in supplied})==len(supplied), 'duplicate_review_id')
    require({r['review_id'] for r in supplied}==set(source), 'review_packet_scope_changed')
    rows=[]
    for row in supplied:
        identity=row['review_id']
        require({k:v for k,v in row.items() if k!='review'}=={k:v for k,v in source[identity].items() if k!='review'}, 'blinded_answer_changed')
        review=row['review']
        qid, repeat, arm=key[identity].rsplit(':',2)
        accepted=(review.get('reviewer')==plan['independent_review']['reviewer'] and review.get('independently_reviewed') is True
            and review.get('reference_accepted') is True)
        semantic=accepted and row['outcome']=='succeeded'
        if semantic:
            require(all(type(review.get(f)) is bool for f in ('complete_correct','partial_correct','severe_temporal_state_error','over_abstention')), 'incomplete_review_judgment')
            require(not(review['complete_correct'] and (review['severe_temporal_state_error'] or review['over_abstention'] or review['partial_correct'])), 'inconsistent_review_judgment')
        rows.append(dict(question_id=qid, sample_id=refs[qid]['sample_id'], episode_id=refs[qid]['episode_id'],
            repeat=int(repeat), arm=arm, outcome=row['outcome'], independently_reviewed=accepted,
            correct=float(review['complete_correct']) if accepted and row['outcome']=='succeeded' else 0.0 if row['outcome']=='failed' else None,
            partial=review.get('partial_correct') if semantic else None,
            severe=review.get('severe_temporal_state_error') if semantic else None,
            over_abstention=review.get('over_abstention') if semantic else None))
    metrics=[]
    for sid in plan['samples']:
        for arm in 'ABCDE':
            subset=[r for r in rows if r['sample_id']==sid and r['arm']==arm]
            expected=3*sum(r['sample_id']==sid for r in refs.values())
            reviewed=sum(r['independently_reviewed'] for r in subset)
            known=[r for r in subset if r['correct'] is not None]
            complete=len(known)==expected
            metrics.append(dict(sample_id=sid, arm=arm, planned_items=expected, saved_items=len(subset),
                successful_items=sum(r['outcome']=='succeeded' for r in subset), failed_items=sum(r['outcome']=='failed' for r in subset),
                saved_outcomes=dict(Counter(r['outcome'] for r in subset)),
                reviewed_items=reviewed, unreviewed_items=sum(r['outcome']=='succeeded' and not r['independently_reviewed'] for r in subset),
                pending_items=expected-len(subset), known_scored_items=len(known),
                primary_complete_correct_rate=average([r['correct'] for r in known]) if complete else None,
                known_subset_correct_rate=average([r['correct'] for r in known]),
                severe_errors=sum(r['severe'] is True for r in subset), over_abstentions=sum(r['over_abstention'] is True for r in subset),
                status='complete' if complete else 'not_fully_independently_validated'))
    contrasts=[]
    for left,right in PAIRS:
        by_conversation=[]
        ready=True
        for sid in plan['samples']:
            paired=[]
            for qid,ref in refs.items():
                if ref['sample_id']!=sid:continue
                l=[r for r in rows if r['question_id']==qid and r['arm']==left]
                r=[r for r in rows if r['question_id']==qid and r['arm']==right]
                if len(l)!=3 or len(r)!=3 or any(v['correct'] is None for v in l+r):
                    ready=False
                    continue
                paired.append(dict(question_id=qid, episode_id=ref['episode_id'], difference=average([v['correct'] for v in l])-average([v['correct'] for v in r]),
                    new_severe_question=any(v['severe'] is True for v in l) and not any(v['severe'] is True for v in r)))
            by_conversation.append(dict(sample_id=sid, complete_paired_questions=len(paired), paired_questions=paired,
                mean_difference=average([p['difference'] for p in paired]), improved=sum(p['difference']>0 for p in paired),
                regressed=sum(p['difference']<0 for p in paired), tied=sum(p['difference']==0 for p in paired),
                new_severe_questions=sum(p['new_severe_question'] for p in paired)))
        interval=None
        effect=None
        if ready and all(c['paired_questions'] for c in by_conversation):
            effect=average([c['mean_difference'] for c in by_conversation])
            seed=int(hashlib.sha256((plan['selection_seed']+':'+left+right).encode()).hexdigest(),16)
            rng=random.Random(seed)
            draws=[]
            for _ in range(2000):
                means=[]
                for c in by_conversation:
                    clusters={}
                    for p in c['paired_questions']:clusters.setdefault(p['episode_id'],[]).append(p['difference'])
                    selected=rng.choices(sorted(clusters),k=len(clusters))
                    means.append(average([v for e in selected for v in clusters[e]]))
                draws.append(average(means))
            draws.sort()
            interval=[draws[49],draws[1949]]
        contrasts.append(dict(contrast=f'{left}-{right}', conversations=by_conversation,
            equal_conversation_difference=effect, descriptive_95_percentile_interval=interval,
            primary_local_benefit_supported=(effect>0 and interval[0]>0 and all(c['mean_difference'] >= 0 for c in by_conversation) and not any(c['new_severe_questions'] for c in by_conversation)) if left+right=='DA' and effect is not None else None,
            status='complete' if effect is not None else 'not_fully_independently_validated'))
    result=dict(reviewer=plan['independent_review']['reviewer'], review_file_sha256=hashlib.sha256(judgments.read_bytes()).hexdigest(),
        scorer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        plan_sha256=hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest(), metrics=metrics, contrasts=contrasts,
        limitations='Three development conversations; descriptive cluster intervals only. Reference acceptance is declared by the named reviewer, not inferred by automation. A positive mean alone is not proof of general benefit.')
    output=output or directory/'independent-review-results.json'
    if output.exists():
        if read(output)!=result:
            raise FileExistsError('review_result_exists; choose a new --output path')
    else:
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2)
            stream.write('\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--judgments',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=score(args.directory.resolve(),args.judgments.resolve(),args.output.resolve() if args.output else None)
    print(json.dumps(dict(primary_status=result['contrasts'][0]['status'])))
