"""Read-only frozen Level E metrics and source-only independent review packets.

Never opens the reference database, scores Gold, generates answers or writes the
execution stage. Unknown evidence, costs and resources are never filled with zero.
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path

from tools.m5 import level_e as e
from tools.m5 import level_c_audit as runtime
from tools.m5 import level_c_semantic_review as semantic
from tools.m5.level_c_results import call_cost

VERSION = 'm5-level-e-reporting-v1'
OPERATIONS = ('query_analysis', 'resolve', 'answer', 'failed_operation')
STAGES = ('retrieval', 'expansion', 'resolve', 'answer')
require = e.require


def implementation_hashes():
    paths = (Path(__file__), Path(runtime.__file__), Path(semantic.__file__), e.ROOT/'tools/m5/level_c_results.py')
    return {str(path.relative_to(e.ROOT)): e.sha(path) for path in paths}


def checked(stage):
    """Require every frozen output before inspecting any evidence or ledger."""
    stage = Path(stage).resolve()
    before = e.sha(stage/'generation-freeze.json')
    plan, lock, items = e.frozen_items(stage)
    require(len(items) == plan['planned_items'] == 2*plan['questions'], 'reporting_full_freeze_required')
    require(e.sha(stage/'generation-freeze.json') == before, 'reporting_freeze_changed')
    return plan, lock, items, before


def records(items):
    result = []
    for item in items:
        operations = item.get('trace', {}).get('operations', {})
        require(set(operations) <= set(OPERATIONS), 'reporting_unexpected_operation')
        # QueryFailure reloads canonical_json, whose sorted object keys are not
        # request order. Failed baseline metadata is stored as failed_operation.
        for name in OPERATIONS:
            for call in operations.get(name, {}).get('calls', []):
                if call.get('outcome') is not None:
                    result.append((item, name, call))
    return result


def attribute_reservations(items, calls, rows):
    """Only a complete serial, ordered correspondence permits arm reservations.

    The producer executes items and operations sequentially. Its ledger has no
    item foreign key, so missing trace records prohibit guessing an allocation.
    """
    if len(calls) != len(rows) or any(i['outcome'] == 'unknown' for i in items):
        return None
    for (_, _, call), row in zip(calls, rows):
        usage = json.loads(row['usage_json']) or {}
        if (call.get('usage', {}) != usage or
                (row['status'] == 'transport_unknown') == bool(call.get('response_received')) or
                row['status'] == 'reserved'):
            return None
    return [(item, name, call, row) for (item, name, call), row in zip(calls, rows)]


def reservation_summary(rows):
    unknown = [r for r in rows if not all(type((json.loads(r['usage_json']) or {}).get(k)) is int
                                         for k in ('prompt_tokens', 'completion_tokens'))]
    return dict(physical_requests=len(rows), reserved_usd=str(sum((Decimal(r['reserved_usd']) for r in rows), Decimal(0))),
                unknown_usage_requests=len(unknown), unknown_reserved_usd=str(sum(
                    (Decimal(r['reserved_usd']) for r in unknown), Decimal(0))))


def resources(stage, optional_path):
    result = dict(cpu_seconds='not_measured', process_peak_rss_kib='not_measured',
                  gpu='not_measured', scope='execution producer did not save process resource sampling')
    if optional_path is None:
        return result
    path = Path(optional_path).resolve()
    before = e.sha(path)
    raw = json.loads(path.read_text())
    require(e.sha(path) == before, 'reporting_resource_changed_during_read')
    require(raw.get('version') == 'm5-level-e-process-resource-v1'
            and raw.get('scope') == 'whole_launcher_process_children'
            and raw.get('plan_sha256') == e.sha(stage/'plan.json')
            and raw.get('execution_started_sha256') == e.sha(stage/'execution-started.json')
            and raw.get('exit_code') == 0 and raw.get('gpu_sampling') == 'not_measured',
            'reporting_resource_binding_changed')
    fields = ('wall_seconds', 'children_user_cpu_seconds', 'children_system_cpu_seconds', 'children_peak_rss_kib')
    require(all(runtime.number(raw.get(k)) for k in fields), 'reporting_resource_number_invalid')
    return dict(scope=raw['scope'], artifact_sha256=e.sha(path), **{k:raw[k] for k in fields},
                gpu='not_measured', per_arm_cpu_rss='not_measured',
                limitation='whole launcher children; cumulative CPU and process lifetime peak RSS, not instantaneous samples')


def audit(stage, process_resources=None):
    stage = Path(stage).resolve()
    plan, lock, items, freeze_sha = checked(stage)
    ledger = runtime.ledger_audit(stage, plan)
    with e.readonly(stage/'physical-requests.sqlite3') as db:
        rows = [dict(r) for r in db.execute('SELECT reserved_usd,status,usage_json FROM physical_requests ORDER BY rowid')]
    calls = records(items)
    for _, _, call in calls:
        require(call.get('requested_model') == plan['policy']['model']
                and call.get('thinking') == {'type':'disabled'} and call.get('reasoning_effort') is None,
                'reporting_model_policy_changed')
    require(len(calls) <= len(rows), 'reporting_adapter_records_exceed_physical_ledger')
    attribution = attribute_reservations(items, calls, rows)
    groups = {}
    for conv in ('all', *e.HOLDOUT):
        for arm in e.ARMS:
            selected = [i for i in items if i['arm'] == arm and (conv == 'all' or i['sample_id'] == conv)]
            selected_ids = {(i['question_id'], i['arm']) for i in selected}
            selected_calls = [(i, name, c) for i, name, c in calls if (i['question_id'], i['arm']) in selected_ids]
            traces = [i.get('trace', {}) for i in selected]
            count = len(selected)
            subsets = dict(all_attempts=lambda i,c:True, retries=lambda i,c:c.get('attempt',1)>1,
                failed_attempts=lambda i,c:c.get('outcome')!='succeeded',
                failed_item_attempts=lambda i,c:i['outcome']=='failed', unknown_item_attempts=lambda i,c:i['outcome']=='unknown')
            cost = {}
            for label, predicate in subsets.items():
                cs = [c for i, _, c in selected_calls if predicate(i,c)]
                reservation = 'not_measured'
                if attribution is not None:
                    reservation = reservation_summary([r for i, _, c, r in attribution if (i['question_id'], i['arm']) in selected_ids and predicate(i,c)])
                cost[label] = dict(adapter_reported=call_cost(cs), physical_reservations=reservation)
            cost['by_operation'] = {name:call_cost([c for _, op, c in selected_calls if op==name]) for name in OPERATIONS}
            reported = cost['all_attempts']['adapter_reported']['reported_tokens']
            successful = sum(i['outcome']=='succeeded' for i in selected)
            groups[conv+'/'+arm] = dict(planned=count, succeeded=successful,
                failed=sum(i['outcome']=='failed' for i in selected), unknown=sum(i['outcome']=='unknown' for i in selected),
                success_rate=successful/count if count else None,
                elapsed_seconds=runtime.distribution([t.get('elapsed_seconds') for t in traces], count),
                stage_seconds={name:runtime.distribution([t.get('stage_seconds',{}).get(name) for t in traces],count) for name in STAGES},
                adapter_attempt_seconds=runtime.distribution([c.get('elapsed_seconds') for _,_,c in selected_calls],len(selected_calls)),
                costs=cost, token_efficiency=dict(reported_tokens_per_successful_item={
                    k:v/successful if successful else None for k,v in reported.items()},
                    scope='reported fields across all attempts divided by successful items; missing usage excluded, not zero',
                    factual_gain_per_token='not_measured'))
    storage = {conv:sum(p.stat().st_size for p in stage.glob(conv+'.sqlite3*') if p.is_file()) for conv in e.HOLDOUT}
    storage['stage_total_bytes'] = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
    ratio = 'not_measured'
    if attribution is not None:
        h = Decimal(groups['all/'+e.ARMS[0]]['costs']['all_attempts']['physical_reservations']['reserved_usd'])
        d = Decimal(groups['all/'+e.ARMS[1]]['costs']['all_attempts']['physical_reservations']['reserved_usd'])
        ratio = str(d/h) if h else None
    require(checked(stage)[3] == freeze_sha, 'reporting_stage_changed_during_audit')
    return dict(version=VERSION, reporting_implementation_sha256=implementation_hashes(),
        generation_freeze_sha256=freeze_sha, planned_items=plan['planned_items'],
        groups=groups, ledger=ledger, reservation_attribution='complete_serial_order_and_usage_verified' if attribution is not None else 'not_measured_missing_or_mismatched_adapter_records',
        completed_adapter_records=len(calls), unattributed_physical_requests=len(rows) if attribution is None else 0,
        dynamic_hybrid_reservation_ratio=ratio, resources=resources(stage,process_resources),
        storage=dict(bytes=storage, scope='post-freeze filesystem sizes; not runtime peak or storage growth'),
        semantic_source_support='not_measured_pending_independent_source_review', actual_invoice='not_accessed',
        gold_read=False, provider_requests=0, raw_text_emitted=False)


def uid(item):
    return e.digest([VERSION, item['question_id'], item['arm']])


def sources_at(stage, lock):
    sources = {}
    for conv in e.HOLDOUT:
        dataset = lock['exports'][conv]['dataset_id']
        with e.readonly(stage/(conv+'.sqlite3')) as db:
            metadata = db.execute('SELECT turn_count FROM conversations WHERE dataset_id=? AND sample_id=?',(dataset,conv)).fetchall()
            rows = [dict(r) for r in db.execute('SELECT '+','.join(semantic.SOURCE_COLUMNS)+
                ' FROM source_turns WHERE dataset_id=? AND sample_id=? ORDER BY position,source_id',(dataset,conv))]
        require(len(metadata)==1 and len(rows)==metadata[0]['turn_count'] and bool(rows)
                and len({r['source_id'] for r in rows})==len(rows), 'reporting_complete_conversation_required')
        sources[conv] = rows
    return sources


def review_projection(stage):
    plan, lock, items, freeze_sha = checked(stage)
    sources = sources_at(Path(stage),lock)
    units = [dict(unit_id=uid(i), conversation_id=i['sample_id'], question=i['question'],
        outcome=i['outcome'], prediction=i.get('prediction'), answer=semantic.answer_projection(i)) for i in items]
    mapping = [dict(unit_id=uid(i),question_id=i['question_id'],sample_id=i['sample_id'],arm=i['arm'],outcome=i['outcome']) for i in items]
    packet = dict(version=VERSION,conversations=sources,units=sorted(units,key=lambda u:u['unit_id']))
    require(checked(stage)[3] == freeze_sha, 'reporting_freeze_changed_during_projection')
    return plan, freeze_sha, packet, sorted(mapping,key=lambda r:r['unit_id'])


def prepare_review(stage, output):
    stage, output = Path(stage).resolve(), Path(output).resolve()
    semantic.outside_stage(stage,output)
    plan, freeze_sha, packet, mapping = review_projection(stage)
    output.mkdir(parents=True,exist_ok=False);output.chmod(0o700)
    e.write(output/'packets.json',packet);e.write(output/'private-mapping.json',mapping)
    manifest = dict(version=VERSION,stage=str(stage),planned=plan['planned_items'],
        generation_freeze_sha256=freeze_sha,plan_sha256=e.sha(stage/'plan.json'),
        reporting_implementation_sha256=implementation_hashes(),
        packets_sha256=e.sha(output/'packets.json'),mapping_sha256=e.sha(output/'private-mapping.json'),
        gold_read=False,provider_requests=0)
    e.write(output/'manifest.json',manifest)
    e.write(output/'review-template.json',dict(version=VERSION,manifest_sha256=e.sha(output/'manifest.json'),
        units=[semantic.pending(u['unit_id']) for u in packet['units']]))
    return dict(planned=plan['planned_items'],reviewed=0,unreviewed=plan['planned_items'],gold_read=False,provider_requests=0)


def validate_review(stage, review_dir, review_file, complete=False):
    stage, review_dir, review_file = Path(stage).resolve(),Path(review_dir).resolve(),Path(review_file).resolve()
    semantic.outside_stage(stage,review_dir)
    plan, freeze_sha, packet, mapping = review_projection(stage)
    paths = [review_dir/n for n in ('manifest.json','packets.json','private-mapping.json')]+[review_file]
    bindings = {p:e.sha(p) for p in paths}
    manifest = json.loads((review_dir/'manifest.json').read_text())
    require(manifest == dict(version=VERSION,stage=str(stage),planned=plan['planned_items'],
        generation_freeze_sha256=freeze_sha,plan_sha256=e.sha(stage/'plan.json'),
        reporting_implementation_sha256=implementation_hashes(),
        packets_sha256=e.sha(review_dir/'packets.json'),mapping_sha256=e.sha(review_dir/'private-mapping.json'),
        gold_read=False,provider_requests=0), 'reporting_review_manifest_changed')
    require(packet==json.loads((review_dir/'packets.json').read_text()) and mapping==json.loads(
        (review_dir/'private-mapping.json').read_text()), 'reporting_review_projection_changed')
    review=json.loads(review_file.read_text())
    require(set(review)=={'version','manifest_sha256','units'} and review['version']==VERSION
        and review['manifest_sha256']==bindings[review_dir/'manifest.json'], 'reporting_review_binding_changed')
    units={u['unit_id']:u for u in packet['units']};rows=review['units']
    require(len(rows)==len(units) and len({r['unit_id'] for r in rows})==len(rows)
        and {r['unit_id'] for r in rows}==set(units), 'reporting_all_review_units_required')
    reviewed={}
    for row in rows:
        key=row['unit_id']
        if row==semantic.pending(key):continue
        unit=units[key];source_map={s['source_id']:s for s in packet['conversations'][unit['conversation_id']]}
        # Unknown execution has no validated final answer; preserve its execution
        # outcome while applying the same not-applicable review contract as failed.
        semantic.check_review({**unit,'outcome':'failed'} if unit['outcome']=='unknown' else unit,row,source_map)
        reviewed[key]=row
    def group(selected):
        selected_rows=[reviewed[r['unit_id']] for r in selected if r['unit_id'] in reviewed]
        semantic_rows=[r for r in selected_rows if r['answer_kind']!='failed']
        return dict(planned=len(selected),reviewed=len(selected_rows),unreviewed=len(selected)-len(selected_rows),
            execution_outcomes=dict(Counter(r['outcome'] for r in selected)),
            answer_kinds=dict(Counter(r['answer_kind'] for r in selected_rows)),
            source_support=semantic.metric(semantic_rows,'source_support','supported','unsupported'),
            citation_support=semantic.metric(semantic_rows,'citation_support','supported','unsupported'),
            abstention=semantic.metric(semantic_rows,'abstention','correct','false'),
            **{field:semantic.metric(semantic_rows,field,True,False) for field in semantic.ERRORS})
    require(all(e.sha(path)==h for path,h in bindings.items()) and checked(stage)[3]==freeze_sha,
        'reporting_review_changed_during_validation')
    require(not complete or len(reviewed)==len(units),'reporting_complete_independent_review_required')
    return dict(version=VERSION,reporting_implementation_sha256=implementation_hashes(),generation_freeze_sha256=freeze_sha,review_manifest_sha256=bindings[review_dir/'manifest.json'],
        completed=len(reviewed)==len(units),overall=group(mapping),
        by_arm={arm:group([r for r in mapping if r['arm']==arm]) for arm in e.ARMS},
        by_conversation={conv:group([r for r in mapping if r['sample_id']==conv]) for conv in e.HOLDOUT},
        interpretation='independent source review, not teacher truth; literal refusal score is not semantic correctness',
        gold_read=False,provider_requests=0,raw_text_emitted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('audit','prepare-review','validate-review','score-review'))
    parser.add_argument('--stage',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--process-resources',type=Path);parser.add_argument('--review-dir',type=Path);parser.add_argument('--reviews',type=Path)
    args=parser.parse_args();semantic.outside_stage(args.stage,args.output)
    if args.action=='prepare-review':result=prepare_review(args.stage,args.output)
    else:
        if args.action=='audit':result=audit(args.stage,args.process_resources)
        else:
            require(args.review_dir is not None and args.reviews is not None,'reporting_review_paths_required')
            require(not args.output.resolve().is_relative_to(args.review_dir.resolve()),'reporting_public_output_inside_private_review')
            result=validate_review(args.stage,args.review_dir,args.reviews,args.action=='score-review')
        e.write(args.output,result)
    print(json.dumps(result))
