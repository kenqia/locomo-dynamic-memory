"""Offline cache/cost summaries; raw text stays in the controlled directory."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sqlite3
import statistics

from locomo_memory.experiment import write_json
from locomo_memory.memory_schemas import ExtractionBatch
from locomo_memory.relation_schemas import RelationBatch
from locomo_memory.retrieval_schemas import QueryAnalysis
from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
from locomo_memory.model import request_messages
from tools.research_v2.observer import STAGES, FIELDS, sha


def static_structure():
    """Synthetic shape only, using production message generation; not live hit evidence."""
    schemas={'extract':ExtractionBatch,'relate':RelationBatch,'query_analysis':QueryAnalysis,
             'resolve':EffectiveResolution,'answer':EvidenceAnswer}
    # Key order mirrors callers, inspected in builds/relations/retrieval/queries/evaluation.
    payloads={'extract':{'sample_id':'conv-26','sources':[]},
              'relate':{'new_memory':{},'history':[],'sources':[],'allowed_labels_by_old_memory':{}},
              'query_analysis':{'question':'synthetic shape only'},
              'resolve':{'operation':'resolve','question':'synthetic shape only','time':{},'analysis':{},'memories':[],'sources':[],'relations':[],'candidates_truncated':False},
              'answer':{'operation':'answer','question':'synthetic shape only','time':{},'status':'sufficient','memories':[],'sources':[],'evidence_truncated':False}}
    records=[]
    for operation,schema in schemas.items():
        messages=request_messages(operation,payloads[operation],schema)
        system=messages[0]['content'].encode()
        records.append({'operation':operation,'stage':STAGES[operation],
                        'system_prompt_plus_schema_bytes':len(system),'system_sha256':sha(system),
                        'user_keys_shape':list(payloads[operation]),
                        'system_content_exported':False})
    return {'status':'offline_structure_only_not_cache_measurement','operations':records,
            'findings':[
                'Production sends a stable system prompt and schema per operation, not one common schema across stages.',
                'User payloads change by fragment, new memory/history, question and selected evidence. Retry feedback can change their suffix.',
                'Full Text must be measured separately: question precedes full sources in the current caller.',
                'Byte-prefix similarity is a local structural proxy, never provider token/cache measurement.',
                'No prompts, schemas, source order or evidence scope were modified.']}


def rows(directory):
    with sqlite3.connect((directory/'observer/budget.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        return [dict(json.loads(r[3]), status=r[0], reservation_nano_cny=r[1],cost_nano_cny=r[2])
                for r in db.execute('SELECT status,reservation,cost,record FROM requests ORDER BY rowid')]


def aggregate(records):
    fields={k:{'reported':sum(r.get('usage',{}).get(k) or 0 for r in records),
               'measured_requests':sum(r.get('usage',{}).get(k) is not None for r in records),
               'missing_requests':sum(r.get('usage',{}).get(k) is None for r in records)} for k in FIELDS}
    paired=[r for r in records if all(r.get('usage',{}).get(k) is not None for k in FIELDS[:3])
            and r['usage']['prompt_cache_hit_tokens']+r['usage']['prompt_cache_miss_tokens']==r['usage']['prompt_tokens']]
    hit=sum(r['usage']['prompt_cache_hit_tokens'] for r in paired)
    prompt=sum(r['usage']['prompt_tokens'] for r in paired)
    return dict(requests=len(records), settled=sum(r['status']=='settled' for r in records),
                unknown=sum(r['status']!='settled' for r in records), usage=fields,
                token_weighted_cache_hit_rate=hit/prompt if prompt else None,
                cache_rate_measured_requests=len(paired),
                known_peak_upper_cny=sum(r['cost_nano_cny'] or 0 for r in records)/1e9,
                unknown_reservation_cny=sum(r['reservation_nano_cny'] for r in records if r['cost_nano_cny'] is None)/1e9,
                elapsed_seconds_known=sum(r.get('elapsed_seconds') or r.get('transport_elapsed_seconds') or 0 for r in records),
                elapsed_seconds_missing=sum(r.get('elapsed_seconds') is None and r.get('transport_elapsed_seconds') is None for r in records),
                semantic_status=dict(Counter(r.get('semantic_status','not_observed') for r in records)),
                returned_models=dict(Counter(r.get('returned_model') or 'missing' for r in records)),
                system_fingerprints=dict(Counter(r.get('system_fingerprint') or 'missing' for r in records)),
                fingerprint_missing=sum(not r.get('system_fingerprint_present') for r in records))


def summarize(directory):
    records=rows(directory)
    result={'status':'offline_actual_observations','currency':'CNY',
            'price_basis':'Peak-rate upper estimate, not provider invoice. No discount assumed for budget.',
            'overall':aggregate(records),'by_stage':{},'by_scope':{},'by_strategy':{},'prefix_measurement':{}}
    for key,field in [('by_stage','stage'),('by_scope','scope'),('by_strategy','strategy')]:
        for value in sorted({r.get(field,'not_applicable') for r in records}):
            result[key][value]=aggregate([r for r in records if r.get(field,'not_applicable')==value])
    for stage in STAGES.values():
        group=[r for r in records if r['stage']==stage]
        previous=[]
        prefix_lengths=[]
        systems=Counter()
        key_orders=Counter()
        for row in group:
            raw=(directory/'observer'/row['wire_path']).read_bytes()
            if sha(raw)!=row['request_sha256']:
                raise ValueError('Request artifact hash mismatch')
            body=json.loads(raw)
            messages=body['messages']
            systems[sha(messages[0]['content'].encode())]+=1
            user=json.loads(messages[1]['content'])
            key_orders[' / '.join(user)]+=1
            encoded=json.dumps(messages,ensure_ascii=False).encode()
            if previous:
                prefix_lengths.append(max(len(os.path.commonprefix([p,encoded])) for p in previous))
            previous.append(encoded)
        result['prefix_measurement'][stage]={'requests':len(group),'distinct_system_hashes':dict(systems),
            'user_top_level_key_orders':dict(key_orders), 'compared_requests':len(prefix_lengths),
            'max_previous_common_prefix_bytes_median':statistics.median(prefix_lengths) if prefix_lengths else None,
            'method':'longest serialized-message byte prefix against prior same-stage requests; not tokens or a cache guarantee'}
    result['request_summaries']=[{k:r.get(k) for k in ('request_id','stage','scope','strategy','question_id','qa_index',
        'build_id','run_id','task_id','fragment_id','operation','logical_id','attempt','model','returned_model','semantic_status','semantic_error_code',
        'request_sha256','response_sha256','request_bytes','status','usage','system_fingerprint',
        'system_fingerprint_present','cost_nano_cny','reservation_nano_cny','elapsed_seconds','transport_elapsed_seconds')}
        for r in records]
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    write_json(args.output,summarize(args.directory) if args.directory else static_structure())
    print(json.dumps({'output':str(args.output),'mode':'actual_offline' if args.directory else 'structure_only'}))
