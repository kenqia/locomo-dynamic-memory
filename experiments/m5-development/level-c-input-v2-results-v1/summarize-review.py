"""Publish paired semantic counts from the fully validated private reviews."""
import json
from pathlib import Path

from tools.m5.level_c import ARMS
from tools.m5.offline import paired, sha, write
from tools.m5.level_c_semantic_review import score


ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / 'var/m5-development/level-c-input-v2-preparation-v1'
REVIEW = ROOT / 'var/m5-development/level-c-input-v2-source-review-v1'
PUBLIC = Path(__file__).resolve().parent


def main():
    destinations = [PUBLIC / name for name in
                    ('semantic-paired-differences.json', 'semantic-review-provenance.json')]
    assert not any(path.exists() for path in destinations), 'preserve_existing_supplement'
    validated = score(STAGE, REVIEW, REVIEW / 'independent-reviews.json')
    published = json.loads((PUBLIC / 'semantic-review-summary.json').read_text())
    assert validated == published and validated['completed']
    mapping = json.loads((REVIEW / 'private-mapping.json').read_text())['units']
    rows = {row['unit_id']: row for row in validated['units']}
    by_question = {}
    for item in mapping:
        by_question.setdefault(item['question_id'], {})[item['arm']] = item
    assert len(by_question) == 100 and all(set(arms) == set(ARMS) for arms in by_question.values())
    pairs = []
    for qid, arms in sorted(by_question.items()):
        h, d = (arms[arm] for arm in ARMS)
        a, b = rows[h['unit_id']], rows[d['unit_id']]
        common = a['answer_kind'] != 'failed' and b['answer_kind'] != 'failed'
        differences = {}
        for field in ('source_support', 'citation_support'):
            av, bv = a[field], b[field]
            known = common and av in ('supported', 'unsupported') and bv in ('supported', 'unsupported')
            differences[field] = int(bv == 'supported') - int(av == 'supported') if known else None
        pairs.append(dict(question_id=qid, sample_id=h['sample_id'], stratum=h['stratum'],
                          both_generation_succeeded=common, **differences))
    summary = {}
    for stratum in ('ordinary', 'diagnostic'):
        selected = [row for row in pairs if row['stratum'] == stratum]
        summary[stratum] = dict(planned_question_pairs=len(selected),
            both_generation_succeeded=sum(row['both_generation_succeeded'] for row in selected),
            metrics={field: paired([row[field] for row in selected if row[field] is not None])
                     for field in ('source_support', 'citation_support')})
    write(destinations[0], dict(summary=summary, pairs=pairs,
        limitation='determinate joint-success subset; exploratory AI source judgments, not causal or teacher truth'))
    review_rows = json.loads((REVIEW / 'independent-reviews.json').read_text())['units']
    packets = json.loads((REVIEW / 'packets.json').read_text())
    names = ('packets.json', 'manifest.json', 'private-mapping.json', 'review-template.json',
             'reviews-conv26-30-v1.json', 'reviews-conv41-42-v1.json', 'independent-reviews.json')
    provenance = dict(kind='ai_assisted_independent',
        reviewers=sorted({row['reviewer'] for row in review_rows}), units=len(review_rows),
        full_conversation_source_turns=sum(len(rows) for rows in packets['conversations'].values()),
        independent_of_generation=all(row['independent_of_generation'] for row in review_rows),
        gold_read_by_reviewers=False, arm_names_and_scores_hidden_in_packets=True,
        all_items_reviewed_including_failures=True, per_unit_double_review=False,
        human_or_teacher_truth=False, reference_hashes={name: sha(REVIEW / name) for name in names},
        quote_records=sum(len(row['source_quotes']) for row in review_rows),
        raw_review_quotes_committed=False,
        limitation='one AI judgment per unit; style may reveal strategy; hashes and quote matching do not prove semantic truth')
    assert len(provenance['reviewers']) == 2 and provenance['independent_of_generation']
    write(destinations[1], provenance)
    print(json.dumps(dict(summary=summary, quote_records=provenance['quote_records']), ensure_ascii=False))


if __name__ == '__main__':
    main()
