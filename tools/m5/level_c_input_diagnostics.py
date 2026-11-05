"""Reconstruct frozen first Dynamic resolve requests offline; emit no evidence text.

Usage: PYTHONPATH=src:. python tools/m5/level_c_input_diagnostics.py \
    --stage var/m5-development/level-c-preparation-v1/final/final-v2 \
    --output experiments/m5-development/level-c-input-diagnostics-v1.json

The token gate is the existing complete-input regex estimate. The transport gate
counts UTF-8 bytes of json.dumps(body['messages'], ensure_ascii=False), including
prompt, schema and the JSON-encoded evidence payload. Neither is provider usage.
No service, model, embedder, credential reader or writable stage connection runs.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import re
from pathlib import Path
import sqlite3
import statistics

from locomo_memory.config import Settings
from locomo_memory.imports import canonical_json
from locomo_memory.model import request_messages, request_token_estimate
from locomo_memory.m5_wire_compression import GUIDANCE, encode_request, ungroup_wire
from locomo_memory.query_schemas import EffectiveResolution
from locomo_memory.resolution_delivery import complete_resolution_input
from locomo_memory.retrieval_schemas import QueryAnalysis
from locomo_memory.temporal import query_memory_times
from tools.m5.level_c_audit import audit as terminal_audit

ROOT = Path(__file__).resolve().parents[2]
DEV = ('conv-26', 'conv-30', 'conv-41', 'conv-42')
MAX_INPUT_BYTES = 160000
ERRORS = ('physical_request_policy_rejected', 'complete_resolution_input_budget_exceeded')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, code):
    if not condition:
        # Only controlled diagnostics; never expose private payloads in exceptions.
        raise ValueError(code)


@contextmanager
def readonly(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        yield connection
    finally:
        connection.close()


def messages_bytes(messages):
    """Exactly BudgetTransport's size domain, not HTTP body bytes or tokens."""
    return json.dumps(messages, ensure_ascii=False).encode('utf-8')


def first_resolve_payload(item, connection):
    """Restore the original caller's order after failed traces were canonicalized.

    Candidate arrays and source_ids preserve their order in frozen item JSON.
    Memories entering expansion are canonical JSON; temporal normalization is the
    same pure function used by QueryService. Source rows and relation JSON are
    fetched with the original QueryService SQL and order, never regenerated.
    Analysis/result field order follows RetrievalService/QueryAnalysis. No final
    resolution or answer is used in reconstructing this first input.
    """
    trace = item['trace']
    conv, dataset, build = trace['sample_id'], trace['dataset_id'], trace['build_id']
    require(conv in DEV and item['sample_id'] == conv, 'development_scope_required')
    initial, expanded = trace['initial'], trace['expanded']
    require(initial['question'] == expanded['question'] == trace['question'], 'trace_question_mismatch')
    # Initial and supplemental memories both enter expansion from canonical JSON.
    memories = {candidate['memory']['memory_id']: json.loads(canonical_json(candidate['memory']))
                for candidate in expanded['candidates']}
    require(len(memories) == len(expanded['candidates']), 'duplicate_candidate_memory')
    sources = {}
    for memory in memories.values():
        require((memory['build_id'], memory['dataset_id'], memory['sample_id']) ==
                (build, dataset, conv), 'candidate_scope_mismatch')
        for sid in memory['source_ids']:
            row = connection.execute('SELECT * FROM source_turns WHERE source_id=? AND dataset_id=? AND sample_id=?',
                                     (sid, dataset, conv)).fetchone()
            require(row is not None, 'missing_development_source')
            sources[sid] = dict(row)
    memories, diagnostics = query_memory_times(memories, sources)
    require(canonical_json(diagnostics) == canonical_json(trace['time_diagnostics']), 'time_diagnostics_mismatch')
    relations = [json.loads(row[0]) for row in connection.execute(
        'SELECT relation_json FROM memory_relations WHERE build_id=? ORDER BY relation_id', (build,))]
    relations = [relation for relation in relations
                 if {relation['old_memory_id'], relation['new_memory_id']} <= memories.keys()]
    require(canonical_json(relations) == canonical_json(trace['relations']), 'relation_snapshot_mismatch')
    # The live trace's beyond-cutoff limitation is added only after resolve.
    timing = {key: trace['time'][key] for key in
              ('requested_date', 'anchor_date', 'origin', 'cutoff', 'cutoff_source_time', 'beyond_cutoff')}
    original = initial['analysis']
    result = (QueryAnalysis.model_validate(original['result']).model_dump(mode='json')
              if original['result'] is not None else None)
    analysis = dict(status=original['status'], result=result, error_code=original['error_code'],
                    model_metadata=original['model_metadata'], prompt_version=original['prompt_version'])
    payload = dict(operation='resolve', question=trace['question'], time=timing, analysis=analysis,
                   memories=list(memories.values()), sources=list(sources.values()), relations=relations,
                   candidates_truncated=initial['initial_truncated'] or expanded['truncated'])
    audit = trace['resolution_budgets']['resolve']
    require(list(memories) == audit['complete_memory_ids'], 'complete_memory_order_mismatch')
    require(list(sources) == audit['source_delivery']['expected_source_ids'], 'complete_source_order_mismatch')
    require(audit['truncated'] is False and audit['omitted_groups'] == [], 'complete_input_not_preserved')
    return payload


def grouping_probe(messages, max_input_bytes):
    """Measure existing reversible wire grouping, including its decoder guidance.

    This transform is reached after complete_resolution_input in production.
    A smaller downstream request never reverses an earlier token-budget rejection.
    """
    before = canonical_json(messages)
    original = json.loads(messages[1]['content'])
    encoded, audit = encode_request({'messages': messages})
    require(canonical_json(messages) == before, 'grouping_probe_mutated_input')
    decoded = json.loads(encoded['messages'][1]['content'])
    if audit['applied']:
        require(encoded['messages'][0]['content'] == messages[0]['content'] + GUIDANCE,
                'grouping_decoder_guidance_mismatch')
        decoded['memories'] = ungroup_wire(decoded)
        del decoded['memory_groups_v1'], decoded['memory_order']
    require(decoded == original, 'grouping_probe_payload_roundtrip_failed')
    encoded_bytes = messages_bytes(encoded['messages'])
    count = len(re.findall(r'\w+|[^\w\s]', encoded_bytes.decode('utf-8')))
    require(count == audit['sent_message_tokens'], 'grouping_probe_count_mismatch')
    return dict(applied=audit['applied'], reason=audit['reason'],
                messages_utf8_bytes=len(encoded_bytes), input_token_estimate=count,
                within_transport_byte_cap=len(encoded_bytes) <= max_input_bytes,
                saved_bytes=len(messages_bytes(messages)) - len(encoded_bytes),
                guidance_included_if_applied=True, roundtrip_input_wire_payload=True,
                roundtrip_input_wire_memories=True, other_payload_fields_unchanged=True)


def inspect_payload(payload, settings, max_input_bytes=MAX_INPUT_BYTES):
    """Reuse production message and complete-input budgeting functions, purely."""
    messages = request_messages('resolve', payload, EffectiveResolution)
    encoded = messages_bytes(messages)
    _, audit = complete_resolution_input(payload, settings)
    estimate = request_token_estimate('resolve', payload, EffectiveResolution)
    require(estimate == audit['input_token_count'], 'pure_budget_disagreement')
    compact = [dict(message) for message in messages]
    wire = json.loads(messages[1]['content'])
    compact[1]['content'] = json.dumps(wire, ensure_ascii=False, separators=(',', ':'))
    require(json.loads(compact[1]['content']) == wire and compact[0] == messages[0], 'compact_probe_changed_data')
    compact_encoded = messages_bytes(compact)
    # Outer HTTP whitespace is erased by BudgetTransport's own reserialization.
    outer_compact = json.dumps({'messages': messages}, ensure_ascii=False, separators=(',', ':'))
    normalized_outer = messages_bytes(json.loads(outer_compact)['messages'])
    require(normalized_outer == encoded, 'outer_normalization_disagreement')
    compact_tokens = len(re.findall(r'\w+|[^\w\s]', compact_encoded.decode('utf-8')))
    require(compact_tokens == estimate, 'compact_probe_changed_regex_count')
    return dict(messages_utf8_bytes=len(encoded), messages_sha256=digest(encoded),
                payload_sha256=digest(canonical_json(payload).encode()),
                input_token_estimate=estimate, within_complete_token_budget=audit['within_budget'],
                within_transport_byte_cap=len(encoded) <= max_input_bytes,
                byte_overrun=max(0, len(encoded) - max_input_bytes),
                token_overrun=max(0, estimate - settings.resolution_input_budget),
                compact_user_json_utf8_bytes=len(compact_encoded),
                compact_user_json_saved_bytes=len(encoded) - len(compact_encoded),
                compact_user_json_within_byte_cap=len(compact_encoded) <= max_input_bytes,
                compact_user_json_token_estimate=compact_tokens,
                outer_http_whitespace_saved_policy_bytes=0,
                memories=len(payload['memories']), sources=len(payload['sources']), relations=len(payload['relations']),
                wire_grouping=grouping_probe(messages, max_input_bytes))


def summarize(rows):
    def distribution(key):
        values = [row[key] for row in rows]
        return dict(min=min(values), median=statistics.median(values), max=max(values), total=sum(values)) if values else None
    return dict(items=len(rows), outcomes=dict(Counter(row['outcome'] for row in rows)),
                observed_failure_codes=dict(Counter(row['observed_error_code'] for row in rows if row['outcome'] == 'failed')),
                byte_cap_exceeded=sum(not row['within_transport_byte_cap'] for row in rows),
                complete_token_budget_exceeded=sum(not row['within_complete_token_budget'] for row in rows),
                both_exceeded=sum(not row['within_transport_byte_cap'] and not row['within_complete_token_budget'] for row in rows),
                byte_only_exceeded=sum(not row['within_transport_byte_cap'] and row['within_complete_token_budget'] for row in rows),
                token_only_exceeded=sum(row['within_transport_byte_cap'] and not row['within_complete_token_budget'] for row in rows),
                both_fit=sum(row['within_transport_byte_cap'] and row['within_complete_token_budget'] for row in rows),
                observed_causes_reproduced=sum(row['observed_cause_reproduced'] for row in rows),
                compact_user_json_byte_cap_exceeded=sum(not row['compact_user_json_within_byte_cap'] for row in rows),
                compact_user_json_both_gates_fit=sum(row['compact_user_json_within_byte_cap'] and row['within_complete_token_budget'] for row in rows),
                compact_user_json_newly_byte_eligible=sum(not row['within_transport_byte_cap'] and row['compact_user_json_within_byte_cap'] for row in rows),
                wire_grouping_applied=sum(row['wire_grouping']['applied'] for row in rows),
                wire_grouping_byte_cap_exceeded=sum(not row['wire_grouping']['within_transport_byte_cap'] for row in rows),
                wire_grouping_original_byte_failures_now_byte_eligible=sum(not row['within_transport_byte_cap'] and row['wire_grouping']['within_transport_byte_cap'] for row in rows),
                wire_grouping_original_byte_only_failures_now_both_gates_fit=sum(not row['within_transport_byte_cap'] and row['within_complete_token_budget'] and row['wire_grouping']['within_transport_byte_cap'] for row in rows),
                wire_grouping_counterfactual_token_failures_now_byte_eligible=sum(not row['within_complete_token_budget'] and row['wire_grouping']['within_transport_byte_cap'] for row in rows),
                wire_grouping_both_gates_fit=sum(row['within_complete_token_budget'] and row['wire_grouping']['within_transport_byte_cap'] for row in rows),
                wire_grouping_token_rejections_bypassed=0,
                message_bytes=distribution('messages_utf8_bytes'), token_estimates=distribution('input_token_estimate'),
                compact_saved_bytes=distribution('compact_user_json_saved_bytes'))


def threshold_scenario(rows, byte_cap, token_budget):
    """Counterfactual gates over original full first inputs, never new runs."""
    def counts(group):
        byte_fail = [row['messages_utf8_bytes'] > byte_cap for row in group]
        token_fail = [row['input_token_estimate'] > token_budget for row in group]
        both = sum(b and t for b, t in zip(byte_fail, token_fail))
        return dict(items=len(group), feasible=sum(not b and not t for b, t in zip(byte_fail, token_fail)),
                    byte_exceeded=sum(byte_fail), token_exceeded=sum(token_fail), both_exceeded=both,
                    byte_only_exceeded=sum(byte_fail)-both, token_only_exceeded=sum(token_fail)-both,
                    infeasible=sum(b or t for b, t in zip(byte_fail, token_fail)))
    return dict(transport_messages_utf8_bytes=byte_cap, complete_input_regex_tokens=token_budget,
                basis='original_complete_first_resolve_without_compaction_or_grouping',
                scope='offline_threshold_arithmetic_only', model_success_evaluated=False,
                production_configuration_changed=False, rerun_authorized=False, increased_budget_authorized=False,
                summary=counts(rows),
                by_stratum={key:counts([row for row in rows if row['stratum'] == key]) for key in ('ordinary','diagnostic')},
                by_conversation={conv:counts([row for row in rows if row['conversation_id'] == conv]) for conv in DEV},
                by_stratum_conversation={key:{conv:counts([row for row in rows if row['stratum'] == key and row['conversation_id'] == conv])
                    for conv in DEV} for key in ('ordinary','diagnostic')})


def run(stage, prior_report=None):
    stage = stage.resolve()
    # This existing guard verifies the original plan, producer identities, all
    # 200 frozen items, protected initial database snapshot, persisted query
    # checkpoints and empty evaluation tables. It never opens the reference DB.
    guard_before = terminal_audit(stage)
    frozen_bytes = (stage/'generation-freeze.json').read_bytes()
    freeze = json.loads(frozen_bytes)
    require(freeze['status'] == 'generation_complete' and freeze['planned_items'] == 200, 'generation_not_frozen')
    settings_bytes, input_bytes = (stage/'settings.json').read_bytes(), (stage/'inputs.json').read_bytes()
    settings, inputs = Settings.model_validate_json(settings_bytes), json.loads(input_bytes)
    require(len(inputs) == 100 and len({item['question_id'] for item in inputs}) == 100
            and all(item['sample_id'] in DEV and item['stratum'] in ('ordinary', 'diagnostic') for item in inputs),
            'fixed_development_inputs_required')
    require(all(sum(item['sample_id'] == conv and item['stratum'] == stratum for item in inputs) == count
                for conv in DEV for stratum, count in (('ordinary', 20), ('diagnostic', 5))),
            'fixed_development_strata_mismatch')
    require(settings.model_name == 'deepseek-flash' and settings.model_max_tokens == 32768,
            'frozen_transport_settings_unsupported')
    names = sorted(name for name in freeze['item_hashes'] if name.endswith('-dynamic.json'))
    require(names == [f'items/{index:03d}-dynamic.json' for index in range(100)], 'dynamic_item_set_incomplete')
    rows = []
    with readonly(stage/'memory.sqlite3') as connection:
        for index, name in enumerate(names):
            item_bytes = (stage/name).read_bytes()
            require(digest(item_bytes) == freeze['item_hashes'][name], 'frozen_item_hash_mismatch')
            item, expected = json.loads(item_bytes), inputs[index]
            require(item['arm'] == 'dynamic' and item['question_id'] == expected['question_id']
                    and item['sample_id'] == expected['sample_id'] and item['stratum'] == expected['stratum'],
                    'frozen_input_identity_mismatch')
            require(item['trace']['question'] == expected['question'], 'frozen_input_question_mismatch')
            require(item['trace']['config'] == settings.snapshot(), 'frozen_settings_mismatch')
            payload = first_resolve_payload(item, connection)
            measured = inspect_payload(payload, settings)
            saved = item['trace']['resolution_budgets']['resolve']
            require(measured['input_token_estimate'] == saved['input_token_count']
                    and saved['input_budget'] == settings.resolution_input_budget
                    and measured['within_complete_token_budget'] == saved['within_budget'], 'frozen_budget_reconstruction_mismatch')
            error = item.get('error_code')
            require(error in (*ERRORS, None), 'unexpected_dynamic_error')
            calls = item['trace']['operations'].get('resolve', {}).get('calls', [])
            if error == 'complete_resolution_input_budget_exceeded':
                reproduced = not measured['within_complete_token_budget'] and not calls
            elif error == 'physical_request_policy_rejected':
                reproduced = measured['within_complete_token_budget'] and not measured['within_transport_byte_cap'] and not calls
            else:
                reproduced = measured['within_complete_token_budget'] and measured['within_transport_byte_cap']
            require(reproduced, 'observed_cause_not_reproduced')
            # Successful item JSON preserves the live nested insertion orders. Its
            # direct un-reordered reconstruction independently cross-checks bytes.
            live_order_match = None
            if item['outcome'] == 'succeeded':
                direct = dict(payload, time={key: item['trace']['time'][key] for key in payload['time']},
                              analysis=item['trace']['initial']['analysis'], relations=item['trace']['relations'])
                require(messages_bytes(request_messages('resolve', direct, EffectiveResolution)) ==
                        messages_bytes(request_messages('resolve', payload, EffectiveResolution)), 'live_order_crosscheck_failed')
                live_order_match = True
            rows.append(dict(item_id=name, item_sha256=digest(item_bytes), question_id=item['question_id'],
                             conversation_id=item['sample_id'], stratum=item['stratum'], outcome=item['outcome'],
                             observed_error_code=error, observed_stage=item['trace'].get('error', {}).get('stage'),
                             observed_resolve_physical_calls=len(calls), observed_cause_reproduced=reproduced,
                             reconstruction='complete_first_resolve', reconstruction_missing=[],
                             successful_live_order_crosscheck=live_order_match, **measured))
    guard_after = terminal_audit(stage)
    require(guard_after == guard_before, 'diagnostic_stage_changed_during_reconstruction')
    require(digest((stage/'generation-freeze.json').read_bytes()) == digest(frozen_bytes)
            and digest((stage/'settings.json').read_bytes()) == digest(settings_bytes)
            and digest((stage/'inputs.json').read_bytes()) == digest(input_bytes),
            'diagnostic_input_files_changed_during_reconstruction')
    return dict(version='m5-level-c-input-diagnostics-v2', status='complete',
                supersedes_report_sha256=digest(prior_report.read_bytes()) if prior_report is not None else None,
                input_integrity=dict(validator='level_c_audit.audit_before_and_after',
                    complete_frozen_items=guard_before['items'], planned_items=guard_before['planned_items'],
                    plan_sha256=guard_before['plan_sha256'], generation_freeze_sha256=guard_before['generation_freeze_sha256'],
                    protected_snapshot_sha256=guard_before['integrity']['protected_snapshot_sha256'],
                    initial_logical_snapshot_reconstructed=guard_before['integrity']['initial_logical_snapshot_reconstructed'],
                    producer_identities_verified=True, frozen_settings_and_inputs_verified=True,
                    candidate_and_trace_checkpoints_verified=True, evaluation_tables_empty=True,
                    source_database_opened=False, before_after_full_audit_equal=True),
                generation_freeze_sha256=digest(frozen_bytes), settings_sha256=digest(settings_bytes), inputs_sha256=digest(input_bytes),
                implementation_sha256={str(path): digest((ROOT/path).read_bytes()) for path in [Path(__file__).resolve().relative_to(ROOT),
                    Path('src/locomo_memory/queries.py'), Path('src/locomo_memory/retrieval.py'),
                    Path('src/locomo_memory/temporal.py'), Path('src/locomo_memory/model.py'),
                    Path('src/locomo_memory/query_payload.py'), Path('src/locomo_memory/query_schemas.py'),
                    Path('src/locomo_memory/retrieval_schemas.py'), Path('src/locomo_memory/config.py'),
                    Path('src/locomo_memory/resolution_delivery.py'),
                    Path('src/locomo_memory/m5_budget.py'), Path('src/locomo_memory/m5_wire_compression.py')]},
                reconstruction=dict(complete_items=len(rows), missing_items=0, complete_memory_order_matches=100,
                    complete_source_order_matches=100, frozen_token_audit_matches=100,
                    successful_live_order_matches=sum(row['successful_live_order_crosscheck'] is True for row in rows),
                    wire_capture_available=False, byte_identity='caller_reconstructed_not_captured_on_wire'),
                historical_generation=dict(model=settings.model_name,
                    query_analysis_thinking_effort=settings.query_analysis_thinking_effort,
                    resolution_thinking_effort=settings.resolution_thinking_effort,
                    answer_thinking_effort=settings.answer_thinking_effort),
                limits=dict(transport_messages_utf8_bytes=MAX_INPUT_BYTES, complete_input_regex_tokens=settings.resolution_input_budget,
                    reserved_output_tokens=settings.model_max_tokens, provider_token_counts=False,
                    first_gate='complete_resolution_input_budget', second_gate='physical_request_policy',
                    size_domain='json.dumps(messages,ensure_ascii=False).encode(utf8)',
                    token_domain='regex_word_punctuation_over_complete_serialized_messages',
                    retry_scope='first_resolve_only_no_retry_feedback'),
                offline_probe=dict(kind='compact_user_payload_json_whitespace_only', parsed_payload_equal=True,
                    source_memory_relation_values_retained=True, system_prompt_schema_unchanged=True,
                    regex_token_estimate_unchanged=True, production_configuration_changed=False,
                    model_noninferiority_evaluated=False, rerun_authorized=False),
                wire_grouping_probe=dict(implementation='m5_wire_compression.encode_request',
                    scope='existing_query_wire_payload_memory_fields', roundtrip_checked_items=len(rows),
                    decoder_guidance_counted=True, complete_token_gate_before_compression=True,
                    token_gate_rejections_bypassed=0, model_decoding_quality_evaluated=False,
                    promotion_authorized=False, production_configuration_changed=False),
                threshold_scenarios=dict(
                    A_bytes_only_doubled=threshold_scenario(rows, 320000, 96000),
                    B_bytes_and_tokens_doubled=threshold_scenario(rows, 320000, 192000),
                    C_bytes_quadrupled_tokens_doubled=threshold_scenario(rows, 640000, 192000)),
                summary=summarize(rows),
                by_stratum={key:summarize([row for row in rows if row['stratum'] == key]) for key in ('ordinary','diagnostic')},
                by_conversation={conv:summarize([row for row in rows if row['conversation_id'] == conv]) for conv in DEV},
                by_stratum_conversation={key:{conv:summarize([row for row in rows if row['stratum'] == key and row['conversation_id'] == conv])
                    for conv in DEV} for key in ('ordinary','diagnostic')},
                provider_calls=0, gold_read=False, holdout_read=False, generation_executed=False, stage_modified=False, items=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prior-report', type=Path)
    args = parser.parse_args()
    require(args.prior_report is None or args.prior_report.resolve() != args.output.resolve(), 'prior_report_must_be_preserved')
    result = run(args.stage, args.prior_report)
    require(args.output.resolve() != args.stage.resolve() and not args.output.resolve().is_relative_to(args.stage.resolve()),
            'output_must_not_modify_stage')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, separators=(',', ':'))
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], summary=result['summary']), ensure_ascii=False))


if __name__ == '__main__':
    main()
