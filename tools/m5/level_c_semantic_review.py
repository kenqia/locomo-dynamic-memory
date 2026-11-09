"""Freeze blinded Level C review packets and validate independent source reviews.

No command generates answers, calls a provider, reads Gold, or writes the stage.
The packet, mapping, manifest, and original review quotes are private artifacts.
Only counts, controlled labels, and opaque unit IDs appear in returned summaries.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from tools.m5.level_c import ARMS, DEV, frozen_items, readonly
from tools.m5.offline import sha, write


VERSION = 'm5-level-c-semantic-review-v1'
ERRORS = ('wrong_person', 'wrong_event', 'wrong_time', 'list_omission')
SUPPORT = ('supported', 'unsupported', 'undetermined', 'not_applicable')
KINDS = ('answered', 'abstained', 'failed', 'undetermined')
STRATA = ('ordinary', 'diagnostic')
SOURCE_COLUMNS = ('source_id', 'dataset_id', 'sample_id', 'session_id', 'dia_id',
                  'speaker', 'session_time', 'text', 'position')
REVIEW_FIELDS = ('reviewer', 'provenance', 'review_kind', 'independent_of_generation',
                 'all_factual_claims_checked', 'answer_kind', 'source_support',
                 'citation_support', 'abstention', *ERRORS, 'source_quotes',
                 'rationale', 'full_conversation_checked', 'evidence_gap')
QUOTE_TARGETS = ('source_support', 'citation_support', 'abstention', *ERRORS)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def unit_id(question_id, arm):
    return digest([VERSION, question_id, arm])


def pending(uid):
    return dict(unit_id=uid, **{field: None for field in REVIEW_FIELDS})


def outside_stage(stage, destination):
    require(not destination.resolve().is_relative_to(stage.resolve()),
            'semantic_output_must_be_outside_stage')


def checked_generation(stage):
    """Verify the *entire* fixed freeze before any evidence database is opened."""
    freeze_sha = sha(stage/'generation-freeze.json')
    plan, items = frozen_items(stage)
    require(sha(stage/'generation-freeze.json') == freeze_sha,
            'semantic_freeze_changed_during_read')
    require(plan.get('planned_items') == 200 and plan.get('questions') == 100
            and plan.get('strata') == dict(ordinary=80, diagnostic=20)
            and set(plan.get('pins', {})) == set(DEV)
            and plan.get('gold_read') is False and plan.get('holdout_read') is False
            and plan.get('bonus_enabled') is False, 'semantic_fixed_scope_required')
    require(len(items) == 200, 'semantic_all_200_items_required')
    inputs = json.loads((stage/'inputs.json').read_text())
    require(len(inputs) == 100
            and all(set(row) == {'question_id', 'sample_id', 'question', 'stratum'}
                    and nonblank(row['question']) for row in inputs),
            'semantic_question_projection_required')
    questions = {row['question_id']: row for row in inputs}
    require(len(questions) == 100, 'semantic_unique_questions_required')
    mapping = []
    for item in items:
        qid, arm = item['question_id'], item['arm']
        require(qid in questions and arm in ARMS, 'semantic_item_identity_invalid')
        question = questions[qid]
        require(question['sample_id'] in DEV and qid.startswith(question['sample_id']+':qa:')
                and item['sample_id'] == question['sample_id']
                and item['stratum'] == question['stratum']
                and question['stratum'] in STRATA, 'semantic_item_identity_invalid')
        mapping.append(dict(unit_id=unit_id(qid, arm), question_id=qid, arm=arm,
                            sample_id=item['sample_id'], stratum=item['stratum']))
    require(len({row['unit_id'] for row in mapping}) == 200,
            'semantic_duplicate_generation_identity')
    expected = {(conv, arm, group): 20 if group == 'ordinary' else 5
                for conv in DEV for arm in ARMS for group in STRATA}
    actual = Counter((row['sample_id'], row['arm'], row['stratum']) for row in mapping)
    require(actual == expected, 'semantic_fixed_conversation_counts_required')
    freeze = json.loads((stage/'generation-freeze.json').read_text())
    require(freeze.get('planned_items') == 200, 'semantic_freeze_count_invalid')
    return plan, items, questions, sorted(mapping, key=lambda row: row['unit_id']), freeze_sha


def conversation_sources(stage, dataset_id):
    """Read explicit source columns and completeness counts from the target only."""
    sources = {}
    with readonly(stage/'memory.sqlite3') as db:
        for conv in DEV:
            meta = db.execute('SELECT turn_count FROM conversations '
                              'WHERE dataset_id=? AND sample_id=?', (dataset_id, conv)).fetchall()
            rows = [dict(row) for row in db.execute(
                'SELECT '+','.join(SOURCE_COLUMNS)+' FROM source_turns '
                'WHERE dataset_id=? AND sample_id=? ORDER BY position,source_id',
                (dataset_id, conv))]
            require(len(meta) == 1 and len(rows) == meta[0]['turn_count'] and bool(rows),
                    'semantic_full_conversation_required')
            require(len({row['source_id'] for row in rows}) == len(rows)
                    and len({row['position'] for row in rows}) == len(rows)
                    and all(nonblank(row['text']) and nonblank(row['source_id']) for row in rows),
                    'semantic_source_identity_invalid')
            sources[conv] = rows
    ids = [row['source_id'] for rows in sources.values() for row in rows]
    require(len(ids) == len(set(ids)), 'semantic_cross_conversation_source_identity')
    return sources


def answer_projection(item):
    trace = item.get('trace') or {}
    require(isinstance(trace, dict), 'semantic_trace_object_required')
    answer = trace.get('answer')
    if answer is None:
        return None
    require(isinstance(answer, dict), 'semantic_answer_object_required')
    # These are the final answer's fields, never resolver decisions or trace scores.
    result = {field: answer.get(field) for field in ('status', 'answer', 'explanation')}
    require(result['status'] in ('sufficient', 'insufficient', 'conflict')
            and nonblank(result['answer'])
            and (result['explanation'] is None or isinstance(result['explanation'], str)),
            'semantic_answer_fields_invalid')
    citations = answer.get('citations', [])
    require(isinstance(citations, list), 'semantic_answer_citations_invalid')
    result['citations'] = []
    for citation in citations:
        require(isinstance(citation, dict) and isinstance(citation.get('source_ids'), list)
                and all(nonblank(sid) for sid in citation['source_ids'])
                and (citation.get('memory_id') is None or nonblank(citation['memory_id'])),
                'semantic_answer_citations_invalid')
        result['citations'].append(dict(memory_id=citation.get('memory_id'),
                                        source_ids=citation['source_ids']))
    return result


def packet(items, questions, sources):
    require(all(item.get('prediction') is None or isinstance(item['prediction'], str)
                for item in items), 'semantic_prediction_field_invalid')
    units = [dict(unit_id=unit_id(item['question_id'], item['arm']),
                  conversation_id=item['sample_id'],
                  question=questions[item['question_id']]['question'], outcome=item['outcome'],
                  prediction=item.get('prediction'), answer=answer_projection(item)) for item in items]
    return dict(version=VERSION, conversations=sources,
                units=sorted(units, key=lambda row: row['unit_id']))


def prepare(stage, output):
    """Create all 200 blinded units with null review labels; never review them."""
    stage, output = Path(stage).resolve(), Path(output).resolve()
    outside_stage(stage, output)
    plan, items, questions, mapping, freeze_sha = checked_generation(stage)
    sources = conversation_sources(stage, plan['dataset_id'])
    packets = packet(items, questions, sources)
    # A concurrent generation mutation must not produce an apparently valid bundle.
    require(checked_generation(stage)[4] == freeze_sha, 'semantic_generation_changed')
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    write(output/'packets.json', packets)
    write(output/'private-mapping.json', dict(version=VERSION, units=mapping))
    manifest = dict(version=VERSION, stage=str(stage), planned=200,
                    generation_freeze_sha256=freeze_sha, plan_sha256=sha(stage/'plan.json'),
                    packets_sha256=sha(output/'packets.json'),
                    mapping_sha256=sha(output/'private-mapping.json'),
                    conversation_sources_sha256=digest(sources),
                    gold_read=False, holdout_read=False, provider_calls=0)
    write(output/'manifest.json', manifest)
    write(output/'review-template.json', dict(version=VERSION,
          manifest_sha256=sha(output/'manifest.json'),
          units=[pending(row['unit_id']) for row in packets['units']]))
    return dict(planned=200, reviewed=0, unreviewed=200, completed=False,
                gold_read=False, provider_calls=0)


def checked_bundle(stage, review_dir):
    """Verify hashes *and* regenerate the allowed projection, without Gold."""
    plan, items, questions, mapping, freeze_sha = checked_generation(stage)
    manifest = json.loads((review_dir/'manifest.json').read_text())
    require(manifest.get('version') == VERSION and manifest.get('planned') == 200
            and manifest.get('stage') == str(stage)
            and manifest.get('generation_freeze_sha256') == freeze_sha
            and manifest.get('plan_sha256') == sha(stage/'plan.json'),
            'semantic_generation_binding_changed')
    require(manifest.get('packets_sha256') == sha(review_dir/'packets.json'),
            'semantic_packet_hash_changed')
    require(manifest.get('mapping_sha256') == sha(review_dir/'private-mapping.json'),
            'semantic_mapping_hash_changed')
    packets = json.loads((review_dir/'packets.json').read_text())
    saved_mapping = json.loads((review_dir/'private-mapping.json').read_text())
    require(saved_mapping == dict(version=VERSION, units=mapping),
            'semantic_mapping_identity_changed')
    sources = conversation_sources(stage, plan['dataset_id'])
    require(manifest.get('conversation_sources_sha256') == digest(sources),
            'semantic_conversation_sources_changed')
    require(packets == packet(items, questions, sources), 'semantic_packet_projection_changed')
    require(sha(stage/'generation-freeze.json') == freeze_sha,
            'semantic_freeze_changed_during_read')
    return packets, mapping


def check_review(unit, row, sources):
    require(set(row) == {'unit_id', *REVIEW_FIELDS}, 'semantic_review_fields_invalid')
    require(nonblank(row['reviewer']) and nonblank(row['provenance'])
            and row['review_kind'] in ('ai_assisted_independent', 'human_independent')
            and row['independent_of_generation'] is True
            and row['all_factual_claims_checked'] is True and nonblank(row['rationale']),
            'semantic_independent_review_required')
    require(row['answer_kind'] in KINDS and row['source_support'] in SUPPORT
            and row['citation_support'] in SUPPORT
            and row['abstention'] in ('correct', 'false', 'undetermined', 'not_applicable'),
            'semantic_review_labels_invalid')
    require(all(row[key] is None or type(row[key]) is bool for key in ERRORS)
            and (row['full_conversation_checked'] is None
                 or type(row['full_conversation_checked']) is bool)
            and (row['evidence_gap'] is None or nonblank(row['evidence_gap'])),
            'semantic_review_flags_invalid')
    quotes = row['source_quotes']
    require(isinstance(quotes, list), 'semantic_review_quotes_required')
    for quote in quotes:
        require(isinstance(quote, dict)
                and set(quote) == {'source_id', 'quote', 'rationale', 'purpose', 'targets'},
                'semantic_quote_fields_invalid')
        require(nonblank(quote['source_id']), 'semantic_quote_source_id_required')
        source = sources.get(quote['source_id'])
        require(source is not None and nonblank(quote['quote'])
                and quote['quote'] in source['text'], 'semantic_same_conversation_verbatim_required')
        require(nonblank(quote['rationale']) and quote['purpose'] in ('support', 'counterevidence', 'gap')
                and isinstance(quote['targets'], list) and bool(quote['targets'])
                and all(target in QUOTE_TARGETS for target in quote['targets'])
                and len(set(quote['targets'])) == len(quote['targets']),
                'semantic_quote_rationale_and_targets_required')

    def evidence(target, purposes):
        return [quote for quote in quotes if target in quote['targets'] and quote['purpose'] in purposes]

    if unit['outcome'] == 'failed':
        require(row['answer_kind'] == 'failed'
                and all(row[key] == 'not_applicable' for key in
                        ('source_support', 'citation_support', 'abstention'))
                and all(row[key] is None for key in ERRORS),
                'semantic_failed_item_must_be_not_applicable')
        return
    require(row['answer_kind'] != 'failed', 'semantic_success_cannot_be_failed')
    if row['answer_kind'] == 'answered':
        require(row['abstention'] == 'not_applicable'
                and row['source_support'] != 'not_applicable'
                and row['citation_support'] != 'not_applicable',
                'semantic_answered_item_labels_invalid')
    elif row['answer_kind'] == 'abstained':
        require(row['abstention'] != 'not_applicable', 'semantic_blanket_abstention_judgment_required')
    else:
        require(row['abstention'] in ('undetermined', 'not_applicable')
                and all(row[key] in ('undetermined', 'not_applicable')
                        for key in ('source_support', 'citation_support'))
                and all(row[key] is None for key in ERRORS),
                'semantic_undetermined_kind_labels_invalid')
    # These conditions validate evidence contracts; they do not infer truth from IDs.
    for key in ('source_support', 'citation_support'):
        if row[key] == 'supported':
            require(bool(evidence(key, ('support',))), 'semantic_supported_label_needs_quote')
        elif row[key] == 'unsupported':
            require(bool(evidence(key, ('counterevidence', 'gap'))),
                    'semantic_unsupported_label_needs_gap_or_counterquote')
    for key in ERRORS:
        if row[key] is True:
            require(bool(evidence(key, ('counterevidence', 'gap'))), 'semantic_error_needs_quote')
    if row['abstention'] == 'false':
        require(bool(evidence('abstention', ('support', 'counterevidence'))),
                'semantic_false_abstention_needs_quote')
    if row['abstention'] == 'correct':
        require(row['full_conversation_checked'] is True and nonblank(row['evidence_gap']),
                'semantic_correct_abstention_needs_full_conversation_gap')
    citations = (unit.get('answer') or {}).get('citations', [])
    cited = {sid for citation in citations for sid in citation['source_ids']}
    if row['citation_support'] == 'supported':
        supporting = {quote['source_id'] for quote in evidence('citation_support', ('support',))}
        # Every claimed supporting quote must actually be cited, and every cited
        # source needs checked support. Otherwise a single good ID could mask a bad one.
        require(bool(cited) and supporting == cited, 'semantic_complete_actual_citation_quotes_required')
    if not cited:
        require(row['citation_support'] != 'supported', 'semantic_empty_citations_cannot_be_supported')


def metric(rows, field, positive, negative):
    values = Counter(row[field] for row in rows)
    denominator = values[positive]+values[negative]
    result = dict(positive=values[positive], negative=values[negative], denominator=denominator,
                  rate=values[positive]/denominator if denominator else None)
    if field in ERRORS:
        # The protocol deliberately uses one null for both cases. Do not invent
        # a distinction, or claim there were zero inapplicable error judgments.
        result['undetermined_or_not_applicable'] = values[None]
    else:
        result.update(undetermined=values['undetermined'], not_applicable=values['not_applicable'])
    return result


def summarize(mapping, units, references):
    def group(selected):
        ids = {row['unit_id'] for row in selected}
        reviewed = [row for uid, row in references.items() if uid in ids]
        semantic = [row for row in reviewed if row['answer_kind'] != 'failed']
        unknown = sum(row['answer_kind'] == 'undetermined'
                      or 'undetermined' in [row[key] for key in
                                           ('source_support', 'citation_support', 'abstention')]
                      for row in semantic)
        return dict(planned=len(ids), reviewed=len(reviewed), unreviewed=len(ids)-len(reviewed),
                    failed=sum(units[uid]['outcome'] == 'failed' for uid in ids),
                    undetermined=unknown,
                    error_undetermined_or_not_applicable=sum(any(row[key] is None for key in ERRORS)
                                                             for row in semantic),
                    answer_kinds=dict(Counter(row['answer_kind'] for row in reviewed)),
                    source_support=metric(semantic, 'source_support', 'supported', 'unsupported'),
                    citation_support=metric(semantic, 'citation_support', 'supported', 'unsupported'),
                    abstention=metric(semantic, 'abstention', 'correct', 'false'),
                    **{key: metric(semantic, key, True, False) for key in ERRORS})

    return dict(overall=group(mapping),
                by_arm={arm: group([row for row in mapping if row['arm'] == arm]) for arm in ARMS},
                by_stratum_arm={group_name+'/'+arm: group([row for row in mapping
                    if row['arm'] == arm and row['stratum'] == group_name])
                    for group_name in STRATA for arm in ARMS},
                by_conversation={conv: group([row for row in mapping if row['sample_id'] == conv]) for conv in DEV},
                by_conversation_stratum_arm={conv+'/'+group_name+'/'+arm: group([row for row in mapping
                    if row['sample_id'] == conv and row['arm'] == arm and row['stratum'] == group_name])
                    for conv in DEV for group_name in STRATA for arm in ARMS})


def validate(stage, review_dir, review_file):
    """Validate complete unit coverage, allowing only untouched null rows as pending."""
    stage, review_dir = Path(stage).resolve(), Path(review_dir).resolve()
    paths = [stage/'generation-freeze.json', stage/'plan.json', review_dir/'manifest.json',
             review_dir/'packets.json', review_dir/'private-mapping.json', Path(review_file)]
    bindings = {path: sha(path) for path in paths}
    packets, mapping = checked_bundle(stage, review_dir)
    reviews = json.loads(Path(review_file).read_text())
    require(isinstance(reviews, dict) and set(reviews) == {'version', 'manifest_sha256', 'units'}
            and reviews['version'] == VERSION
            and reviews['manifest_sha256'] == sha(review_dir/'manifest.json'),
            'semantic_review_manifest_binding_required')
    units = {row['unit_id']: row for row in packets['units']}
    rows = reviews['units']
    require(isinstance(rows, list) and len(rows) == 200
            and all(isinstance(row, dict) and isinstance(row.get('unit_id'), str) for row in rows),
            'semantic_all_200_review_units_required')
    require(len({row['unit_id'] for row in rows}) == 200
            and {row['unit_id'] for row in rows} == set(units),
            'semantic_review_unit_identity_required')
    references = {}
    for row in rows:
        uid = row['unit_id']
        if row == pending(uid):
            continue
        unit = units[uid]
        sources = {source['source_id']: source for source in packets['conversations'][unit['conversation_id']]}
        check_review(unit, row, sources)
        references[uid] = row
    require(all(sha(path) == expected for path, expected in bindings.items()),
            'semantic_review_artifacts_changed_during_validation')
    require(checked_generation(stage)[4] == bindings[stage/'generation-freeze.json'],
            'semantic_generation_changed_during_validation')
    result = dict(version=VERSION, generation_freeze_sha256=bindings[stage/'generation-freeze.json'],
                  completed=len(references) == 200,
                  summary=summarize(mapping, units, references),
                  units=[dict(unit_id=uid, reviewed=uid in references,
                              **{key: references[uid][key] if uid in references else None for key in
                                 ('answer_kind', 'source_support', 'citation_support', 'abstention', *ERRORS)})
                         for uid in sorted(units)], gold_read=False, provider_calls=0)
    return result


def score(stage, review_dir, review_file):
    """Publish semantics only when all 200 units have explicit independent reviews."""
    result = validate(stage, review_dir, review_file)
    require(result['completed'], 'semantic_all_200_independent_reviews_required')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'validate', 'score'))
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--review-dir', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        require(args.reviews is None and args.output is None, 'semantic_prepare_uses_review_dir_only')
        result = prepare(args.stage, args.review_dir)
    else:
        require(args.reviews is not None, 'semantic_reviews_file_required')
        if args.output is not None:
            outside_stage(args.stage, args.output)
            require(not args.output.resolve().is_relative_to(args.review_dir.resolve()),
                    'semantic_public_output_must_be_outside_private_review_dir')
        operation = validate if args.action == 'validate' else score
        result = operation(args.stage, args.review_dir, args.reviews)
        if args.output is not None:
            write(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
