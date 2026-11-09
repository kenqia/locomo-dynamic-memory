"""Read-only Level C runtime/cost/integrity audit; never score or open Gold.

Only numeric aggregates and controlled labels leave this module. The terminal
command requires the complete generation freeze; progress reads item files only.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

from locomo_memory.usage import provider_usage
from tools.m5.level_c import ARMS, DEV, TABLES, frozen_items, readonly, verify_plan
from tools.m5.offline import sha, write

QUERY_TABLES = ('candidate_queries', 'candidate_expansions', 'query_traces')
INITIAL_TABLES = tuple(sorted((*TABLES, 'import_artifacts', 'relation_attempts',
                             'relation_provider_calls', *QUERY_TABLES)))
EXECUTION_TABLES = ('evaluation_inputs', 'evaluation_runs', 'evaluation_run_items')
LEDGER_STATES = ('reserved', 'response_received', 'response_usage_unknown', 'transport_unknown')
LOCAL_REJECTIONS = ('physical_request_policy_rejected', 'physical_request_budget_exhausted')
OPERATIONS = ('query_analysis', 'resolve', 'answer', 'failed_operation')
STAGES = ('retrieval', 'expansion', 'resolve', 'answer')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def distribution(values, expected=None):
    data = [v for v in values if number(v)]
    return dict(observed=len(data), missing=None if expected is None else expected-len(data),
                total=sum(data), p50=float(np.quantile(data,.5)) if data else None,
                p95=float(np.quantile(data,.95)) if data else None)


def completed_calls(calls):
    # A started checkpoint can be a local rejection or crash. The ledger alone
    # establishes physical sends/reservations; never count that record as a send.
    return [c for c in calls if c.get('outcome') is not None]


def summaries(items, planned=None):
    result = {}
    for stratum in ('ordinary','diagnostic'):
        for arm in ARMS:
            group = [i for i in items if i['arm']==arm and i['stratum']==stratum]
            denominator = planned[stratum] if planned is not None else len(group)
            traces = [i.get('trace',{}) for i in group]
            operations = {}
            for name in OPERATIONS:
                records = [c for t in traces for c in t.get('operations',{}).get(name,{}).get('calls',[])]
                calls = completed_calls(records)
                operations[name] = dict(operation_traces=sum(name in t.get('operations',{}) for t in traces),
                    completed_adapter_attempt_records=len(calls), unresolved_started_records=len(records)-len(calls),
                    usage=provider_usage(calls),
                    adapter_attempt_seconds=distribution([c.get('elapsed_seconds') for c in calls],len(calls)))
            result[stratum+'/'+arm] = dict(planned=denominator, completed=len(group),
                pending=denominator-len(group), succeeded=sum(i['outcome']=='succeeded' for i in group),
                failed=sum(i['outcome']=='failed' for i in group),
                success_rate=sum(i['outcome']=='succeeded' for i in group)/denominator if denominator else None,
                local_policy_rejected_items=sum(i.get('error_code')==LOCAL_REJECTIONS[0] for i in group),
                local_budget_rejected_items=sum(i.get('error_code')==LOCAL_REJECTIONS[1] for i in group),
                item_elapsed_seconds=distribution([t.get('elapsed_seconds') for t in traces],len(group)),
                stage_elapsed_seconds={stage:distribution([t.get('stage_seconds',{}).get(stage) for t in traces],len(group)) for stage in STAGES},
                operations=operations)
    return result


def scope_check(plan, items, inputs):
    require(set(plan['pins'])==set(DEV) and plan.get('bonus_enabled') is False,
            'audit_scope_or_bonus_changed')
    require(plan.get('holdout_read') is False and plan.get('gold_read') is False,
            'audit_plan_claims_annotation_access')
    by_id = {i['question_id']:i for i in inputs}
    for item in items:
        require(item['question_id'] in by_id, 'audit_question_identity_changed')
        identity = by_id[item['question_id']]
        require(item['sample_id']==identity['sample_id'] and item['stratum']==identity['stratum'], 'audit_question_identity_changed')
        trace = item.get('trace',{})
        require(item['outcome']=='failed' or bool(trace), 'audit_success_without_trace')
        if 'question' in trace:
            require(trace['question']==identity['question'], 'audit_trace_question_changed')
        if 'question_id' in trace:
            require(trace['question_id']==item['question_id'], 'audit_question_identity_changed')
        if 'strategy' in trace:
            require(trace['strategy']==item['arm'], 'audit_unplanned_query_strategy')
        require(not any(k in trace for k in ('raw_fallback','strategy_recovery','raw_source_stages',
            'answer_boundary','evidence_selection','initial_resolution')), 'audit_unplanned_query_strategy')
        require(not trace.get('raw_context'), 'audit_unplanned_query_strategy')
        payloads = [trace,*trace.get('operations',{}).values()]
        for key in ('retrieval','initial','expanded','expansion'):
            candidate=trace.get(key)
            if isinstance(candidate,dict):
                payloads.append(candidate)
                if 'question' in candidate:
                    require(candidate['question']==identity['question'], 'audit_trace_question_changed')
        require(not any(str(k).startswith('m5_') for value in payloads for k in value), 'audit_bonus_trace_present')
        require(item['sample_id'] in DEV and item['arm'] in ARMS, 'audit_item_outside_scope')
        expected_build, expected_sample = plan['pins'][item['sample_id']], item['sample_id']
        stack = [item.get('trace',{})]
        while stack:
            value = stack.pop()
            if isinstance(value,dict):
                if 'build_id' in value:
                    require(value['build_id']==expected_build, 'audit_trace_cross_build')
                if 'sample_id' in value:
                    require(value['sample_id']==expected_sample, 'audit_trace_cross_conversation')
                stack.extend(value.values())
            elif isinstance(value,list):
                stack.extend(value)


def database_integrity(stage, plan, items):
    """Reconstruct prepare's exact logical snapshot, with query tables empty.

    No source DB is opened. No evaluation rows are read, even if injected: their
    counts must be zero. Every initial non-query table participates in the hash.
    """
    with readonly(stage/'memory.sqlite3') as db:
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(set(INITIAL_TABLES) <= names and names <= set(INITIAL_TABLES+EXECUTION_TABLES),
                'audit_unexpected_database_tables')
        for name in EXECUTION_TABLES:
            if name in names:
                require(db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]==0,
                        'audit_evaluation_rows_present')
        digest = hashlib.sha256()
        for name in INITIAL_TABLES:
            rows = [] if name in QUERY_TABLES else sorted(
                json.dumps(tuple(r),ensure_ascii=False,default=str) for r in db.execute('SELECT * FROM '+name))
            digest.update(json.dumps([name,rows],ensure_ascii=False).encode())
        require(digest.hexdigest()==plan['database_snapshot'], 'audit_frozen_build_or_source_changed')
        actual = {r[0]:r[1] for r in db.execute('SELECT build_id,sample_id FROM build_versions')}
        require(actual=={bid:conv for conv,bid in plan['pins'].items()}, 'audit_database_build_scope_changed')
        require({r[0] for r in db.execute('SELECT DISTINCT sample_id FROM source_turns')}==set(DEV),
                'audit_database_conversation_scope_changed')
        pins = tuple(plan['pins'].values())
        counts = {}
        for name in QUERY_TABLES:
            require(db.execute('SELECT COUNT(*) FROM '+name+' WHERE build_id NOT IN (?,?,?,?)',pins).fetchone()[0]==0,
                    'audit_query_row_cross_build')
            counts[name] = db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
        linked = {'candidate_queries':set(), 'candidate_expansions':set()}
        for item in items:
            trace = item.get('trace',{})
            initial = trace.get('initial',{}) if item['arm']=='dynamic' else trace.get('retrieval',{})
            expanded = trace.get('expanded',{}) if item['arm']=='dynamic' else trace.get('expansion',{})
            for name, key, value in (('candidate_queries','query_id',initial),
                                     ('candidate_expansions','expansion_id',expanded)):
                if not isinstance(value,dict) or not value.get(key):
                    continue
                row = db.execute('SELECT result_json FROM '+name+' WHERE '+key+'=?',(value[key],)).fetchone()
                require(row is not None and json.loads(row[0])==value, 'audit_candidate_checkpoint_changed')
                linked[name].add(value[key])
        require(all(counts[name]==len(ids) for name,ids in linked.items()), 'audit_unattributed_candidate_rows')
        # Dynamic saves its trace; Hybrid baseline retains its trace in item JSON.
        dynamic = [i for i in items if i['arm']=='dynamic' and i.get('trace',{}).get('trace_id')]
        for item in dynamic:
            trace = item['trace']
            row = db.execute('SELECT result_json FROM query_traces WHERE trace_id=?',(trace['trace_id'],)).fetchone()
            require(row is not None and json.loads(row[0])==trace, 'audit_dynamic_trace_checkpoint_changed')
        require(counts['query_traces']==len(dynamic), 'audit_unattributed_query_traces')
        return dict(initial_logical_snapshot_reconstructed=True, protected_snapshot_sha256=digest.hexdigest(),
                    build_source_memory_relation_projection_index_unchanged=True,
                    development_conversations=4, complete_builds=4, query_table_counts=counts,
                    dynamic_trace_checkpoints_verified=len(dynamic), evaluation_tables_empty=True,
                    no_source_database_opened=True)


def ledger_audit(stage, plan):
    with readonly(stage/'physical-requests.sqlite3') as db:
        policy = json.loads(db.execute('SELECT json FROM policy WHERE singleton=1').fetchone()[0])
        rows = db.execute('SELECT reserved_usd,status,usage_json FROM physical_requests').fetchall()
    proposed = plan['policy']
    expected = dict(max_requests=proposed['max_requests'],max_usd=str(Decimal(proposed['max_usd'])),
        model=proposed['model'],input_rate=str(Decimal(proposed['input_usd_per_million'])),
        output_rate=str(Decimal(proposed['output_usd_per_million'])),
        max_input_bytes=proposed['max_input_bytes'],max_output_tokens=proposed['max_output_tokens'])
    require(policy==expected, 'audit_ledger_policy_changed')
    states, usage = Counter(), Counter()
    reserved, known_peak, unknown_reserved = Decimal(0), Decimal(0), Decimal(0)
    unknown, partial = 0, 0
    reservations_by_status = {s:Decimal(0) for s in LEDGER_STATES}
    for row in rows:
        amount = Decimal(row['reserved_usd'])
        require(amount.is_finite() and amount>=0, 'audit_invalid_reservation')
        require(row['status'] in LEDGER_STATES, 'audit_unknown_ledger_state')
        states[row['status']] += 1
        reservations_by_status[row['status']] += amount
        reserved += amount
        fields = json.loads(row['usage_json'])
        fields = fields if isinstance(fields,dict) else {}
        valid = {k:v for k,v in fields.items() if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int and v>=0}
        usage.update(valid)
        if not all(k in valid for k in ('prompt_tokens','completion_tokens')):
            unknown += 1
            partial += bool(valid)
            unknown_reserved += amount
        else:
            known_peak += (Decimal(valid['prompt_tokens'])*Decimal(policy['input_rate'])+
                           Decimal(valid['completion_tokens'])*Decimal(policy['output_rate']))/1000000
    require(len(rows)<=policy['max_requests'] and reserved<=Decimal(policy['max_usd']), 'audit_budget_cap_exceeded')
    return dict(physical_ledger_requests=len(rows), request_statuses={s:states[s] for s in LEDGER_STATES},
        reserved_usd=str(reserved), reservations_by_status_usd={s:str(v) for s,v in reservations_by_status.items()},
        unknown_usage_requests=unknown, partial_usage_requests=partial, unknown_usage_reserved_usd=str(unknown_reserved),
        reported_usage=dict(usage), known_complete_usage_peak_cache_miss_upper_usd=str(known_peak),
        all_reported_fields_peak_cache_miss_upper_usd=str((Decimal(usage['prompt_tokens'])*Decimal(policy['input_rate'])+
            Decimal(usage['completion_tokens'])*Decimal(policy['output_rate']))/1000000),
        reported_cost_scope='reported fields only; missing usage remains unknown and fully reserved',
        reported_partial_usage_included_in_token_totals=True, unknown_reservations_retained=True,
        remaining_requests=policy['max_requests']-len(rows),
        remaining_reserved_capacity_usd=str(Decimal(policy['max_usd'])-reserved),
        actual_invoice_usd='not_accessed', policy_verified=True)


def audit(stage):
    stage = stage.resolve()
    plan, items = frozen_items(stage)  # Requires all planned frozen item hashes.
    inputs = json.loads((stage/'inputs.json').read_text())
    scope_check(plan,items,inputs)
    integrity = database_integrity(stage,plan,items)
    ledger = ledger_audit(stage,plan)
    records = [c for i in items for op in i.get('trace',{}).get('operations',{}).values() for c in op.get('calls',[])]
    complete = completed_calls(records)
    requested, returned, effort = Counter(), Counter(), Counter()
    missing_model = 0
    for item in items:
        for operation, metadata in item.get('trace',{}).get('operations',{}).items():
            for call in metadata.get('calls',[]):
                if call.get('outcome') is None:
                    continue
                require(call.get('requested_model')==plan['policy']['model'], 'audit_requested_model_changed')
                require(call.get('thinking')=={'type':'disabled'} and call.get('reasoning_effort') is None,
                        'audit_thinking_policy_changed')
                actual_effort = 'disabled'
                require(type(call.get('max_tokens')) is int and 1<=call['max_tokens']<=plan['policy']['max_output_tokens'],
                        'audit_output_token_policy_changed')
                requested[plan['policy']['model']] += 1
                name = call.get('returned_model')
                if name is None:
                    missing_model += 1
                else:
                    require(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9._/-]{1,128}',name), 'audit_invalid_returned_model')
                    returned[name] += 1
                effort[actual_effort if actual_effort in ('disabled','low','high') else 'unknown'] += 1
    require(len(complete)<=ledger['physical_ledger_requests'], 'audit_more_adapter_attempts_than_ledger_requests')
    freeze = json.loads((stage/'generation-freeze.json').read_text())
    resources = {k:v if number(v) else None for k in ('wall_seconds','cpu_seconds','process_peak_rss_kib')
                 for v in [freeze.get('resources',{}).get(k)]}
    resources['gpu_used'] = freeze.get('resources',{}).get('gpu_used') if type(freeze.get('resources',{}).get('gpu_used')) is bool else None
    return dict(status='generation_complete',plan_sha256=sha(stage/'plan.json'),
        generation_freeze_sha256=sha(stage/'generation-freeze.json'), planned_items=plan['planned_items'],
        items=len(items), groups=summaries(items), integrity=integrity, ledger=ledger, resources=resources,
        model_identity=dict(requested_models=dict(requested),returned_models=dict(returned),
                            calls_without_returned_model=missing_model,thinking_efforts=dict(effort)),
        completed_adapter_attempt_records=len(complete), unresolved_started_records=len(records)-len(complete),
        ledger_requests_without_completed_adapter_record=ledger['physical_ledger_requests']-len(complete),
        latency_scope='saved item wall time and explicitly saved stage times; failed baseline stage times may be missing; adapter attempt time is separate',
        physical_request_scope='physical_requests ledger only; local rejections and started-only diagnostic records are not counted as sends',
        gold_read=False,holdout_read=False,bonus_enabled=False,raw_text_emitted=False,
        quality_metrics='not_measured_by_this_audit')


def progress(stage):
    """No database access and no dependency on a complete generation freeze."""
    stage = stage.resolve()
    plan,_,inputs = verify_plan(stage)
    items, incomplete = [], 0
    for index, question in enumerate(inputs):
        for arm in ARMS:
            path = stage/f'items/{index:03d}-{arm}.json'
            if not path.exists():
                continue
            try:
                item = json.loads(path.read_text())
            except json.JSONDecodeError:
                incomplete += 1  # Producer may still be writing this file.
                continue
            require(all(item[k]==v for k,v in dict(question_id=question['question_id'],
                sample_id=question['sample_id'],stratum=question['stratum'],arm=arm).items()),
                'audit_progress_item_identity_changed')
            require(item['outcome'] in ('succeeded','failed'), 'audit_progress_item_not_terminal')
            items.append(item)
    scope_check(plan,items,inputs)
    return dict(status='partial_progress_not_final_audit',planned_items=plan['planned_items'],
        completed_items=len(items),incomplete_item_files=incomplete,
        groups=summaries(items,plan['strata']),database_read=False,gold_read=False,raw_text_emitted=False)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--progress',action='store_true')
    args = parser.parse_args()
    result = progress(args.stage) if args.progress else audit(args.stage)
    write(args.output,result)
    print(json.dumps(result))
