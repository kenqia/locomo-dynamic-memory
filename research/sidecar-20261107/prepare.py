"""Prepare a bounded, deterministic real-export study without running inference."""
import argparse, hashlib, json
from itertools import combinations
from pathlib import Path

SIDES = ('conv-26', 'conv-30')
SALT = 'sidecar-diagnostic-real-v1-20261107'
def hash_bytes(b): return hashlib.sha256(b).hexdigest()
def dump(p, obj): p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--exports',type=Path,required=True);parser.add_argument('--private',type=Path,required=True);args=parser.parse_args()
    args.private.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((args.exports/'six-memory-exports-manifest.json').read_text());rows=[];packet=[]
    for sid in SIDES:
        entry=next(x for x in manifest['builds'] if x['sample_id']==sid);raw=(args.exports/entry['file']).read_bytes();assert hash_bytes(raw)==entry['sha256'];data=json.loads(raw)
        # Exact controlled input copy; no SQLite, QA or Gold is opened.
        (args.private/entry['file']).write_bytes(raw)
        memories=data['memories'];sources={s['source_id']:s for s in data['sources']}
        rank=lambda identifier:hash_bytes((SALT+'|'+sid+'|'+identifier).encode())
        selected=sorted(memories,key=lambda m:rank(m['memory_id']))[:20]
        units=[]
        for m in selected:
            units.append({'unit_id':sid+'|claim|'+m['memory_id'],'kind':'claim','memory':m,'sources':[sources[x] for x in m['source_ids']]})
        pairs=[(a,b) for a,b in combinations(memories,2) if a['memory_type']=='event' and b['memory_type']=='event' and a['entity_id']==b['entity_id'] and a['state_dimension']==b['state_dimension']]
        pairs=sorted(pairs,key=lambda pair:rank('|'.join(sorted([pair[0]['memory_id'],pair[1]['memory_id']]))))[:10]
        assert len(pairs)==10
        for a,b in pairs:
            ids=sorted(set(a['source_ids'])|set(b['source_ids']))
            units.append({'unit_id':sid+'|pair|'+'|'.join(sorted([a['memory_id'],b['memory_id']])),'kind':'pair','memories':[a,b],'sources':[sources[x] for x in ids]})
        entities=sorted({m['entity_id'] for m in memories} & {s['speaker'] for s in sources.values()})[:2];assert len(entities)==2
        queries=[]
        for entity in entities:
            for dimension,question in [('residence',f'Where does {entity} live?'),('birth_year',f"What is {entity}'s birth year?")]:
                qid=sid+'|query|'+entity+'|'+dimension;relevant=[m for m in memories if m['entity_id']==entity];ids=sorted({s for m in relevant for s in m['source_ids']})
                units.append({'unit_id':qid,'kind':'query','question':question,'dimension':dimension,'entity':entity,'as_of':None,'memories':relevant,'sources':[sources[x] for x in ids]})
                queries.append({'unit_id':qid,'question':question,'dimension':dimension,'entity':entity})
        dump(args.private/(sid+'-reference-packet.json'),{'sample_id':sid,'instructions':'Independent reference: use raw cited sources. Do not infer labels from extracted Memory or prior Sidecar diagnostics. Distinguish ambiguous sources from unsupported extraction. No model/provider calls. See frozen protocol for label fields.','units':units})
        rows.append({'sample_id':sid,'file':entry['file'],'sha256':entry['sha256'],'build_id':entry['build_id'],'build_fingerprint':entry['build_fingerprint'],'memories':len(memories),'source_turns':len(sources),'claim_ids':[m['memory_id'] for m in selected],'pair_ids':[[a['memory_id'],b['memory_id']] for a,b in pairs],'queries':queries,'reference_packet_sha256':hash_bytes((args.private/(sid+'-reference-packet.json')).read_bytes())})
    plan={'protocol':'real-sidecar-diagnostic-v1','salt':SALT,'input_manifest_sha256':hash_bytes((args.exports/'six-memory-exports-manifest.json').read_bytes()),'builds':rows,'reference_units':68,'claim_reference_units':40,'pair_reference_units':20,'query_reference_units':8,'scope':'Exposed development/regression only; not unseen test; no teacher hidden data'}
    dump(Path(__file__).with_name('frozen-input-plan.json'),plan)
    print(json.dumps({'builds':2,'claims':sum(x['memories'] for x in rows),'reference_units':68,'private_output':str(args.private)}))
if __name__=='__main__':main()
