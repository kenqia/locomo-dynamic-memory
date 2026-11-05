"""Create compact, auditable derived artifacts without changing original replay files."""
from collections import Counter
import argparse
import gzip
import json
import sqlite3
import subprocess
from pathlib import Path

from tools.m5.offline import ROOT, ORIGIN, RUN, sha, write


def run(delivery='delivery-v1', label='delivery-analysis-v1'):
    if any(not value.replace('-', '').isalnum() for value in (delivery, label)):
        raise ValueError('invalid_artifact_label')
    base = ROOT/'experiments/m5-development'
    output = base/label
    output.mkdir(exist_ok=False)
    rows = json.loads((base/delivery/'per-question-metrics.json').read_text())
    connection = sqlite3.connect(ORIGIN.resolve().as_uri()+'?mode=ro',uri=True)
    connection.execute('PRAGMA query_only=ON')
    original = {r['question_id']:r for r in (json.loads(raw) for raw, in connection.execute(
        "SELECT item_json FROM evaluation_run_items WHERE run_id=? AND json_extract(item_json,'$.strategy')='hybrid_no_resolution'",(RUN,)))}
    parity = []
    for row in rows:
        historic = original[row['question_id']]
        trace = historic['result']['trace']
        context = trace.get('delivered_memories', trace.get('answer_context_items', []))
        predicted = row['arms']['H']['memory_ids']['delivered']
        parity.append(dict(question_id=row['question_id'],historical_status=historic['status'],
            compare_scope='delivered_memories' if 'delivered_memories' in trace else 'would_be_answer_context_items',
            packet_equal=predicted==[m['memory_id'] for m in context],
            input_equal=row['arms']['H']['parity']['initial'],expansion_equal=row['arms']['H']['parity']['expansion']))
    connection.close()
    write(output/'hybrid-packet-parity.json',dict(denominator=757,
        packet_equal=sum(r['packet_equal'] for r in parity),initial_equal=sum(r['input_equal'] for r in parity),
        expansion_equal=sum(r['expansion_equal'] for r in parity),items=parity,
        correction='Original delivery-v1 parity compared only delivered_memories, absent on four failed/unknown rows. Those compare planned answer_context_items here; no real delivery or success claimed.'))
    compact = []
    for row in rows:
        compact.append(dict(question_id=row['question_id'],sample_id=row['sample_id'],category=row['category'],scorable=row['scorable'],
            arms={name:{key:arm.get(key) for key in ('status','error_code','recall','stage_recall','wall_seconds','wire_compression')}
                  for name,arm in row['arms'].items()}))
    write(output/'per-question-metrics.json',compact)
    cases = {}
    for name in ('B1','B2','B3','B4'):
        changes = []
        for row in rows:
            if not row['scorable']:
                continue
            arm,control = row['arms'][name],row['arms']['D']
            delta = arm['stage_recall']['delivered']-control['stage_recall']['delivered']
            expanded_delta = arm['stage_recall']['expanded']-control['stage_recall']['expanded']
            if delta or expanded_delta:
                changes.append(dict(question_id=row['question_id'],sample_id=row['sample_id'],category=row['category'],
                    delivered_delta=delta,expanded_delta=expanded_delta,
                    added_delivered_ids=sorted(set(arm['memory_ids'].get('delivered',[]))-set(control['memory_ids'].get('delivered',[]))),
                    lost_delivered_ids=sorted(set(control['memory_ids'].get('delivered',[]))-set(arm['memory_ids'].get('delivered',[])))))
        cases[name]=sorted(changes,key=lambda c:(c['delivered_delta'],c['question_id']))
    write(output/'failure-and-change-cases.json',cases)
    graph_paths=[p for row in rows for p in (row['arms']['B1'].get('graph') or {}).get('paths',{}).values() if p]
    write(output/'graph-path-summary.json',dict(added_path_count=len(graph_paths),
        path_lengths=dict(Counter(len(path) for path in graph_paths)),
        queries_with_two_hops=sum(any(len(p)>1 for p in (row['arms']['B1'].get('graph') or {}).get('paths',{}).values()) for row in rows),
        connectivity_is_semantic_truth=False))
    artifacts={}
    for run_label in ('replay-v1',delivery):
        raw=base/run_label/'per-question-metrics.json'
        packed=output/(run_label+'-raw-results.json.gz')
        with raw.open('rb') as source, packed.open('xb') as destination:
            with gzip.GzipFile(fileobj=destination,mode='wb',mtime=0,filename='') as encoded:
                for block in iter(lambda:source.read(1024*1024),b''):
                    encoded.write(block)
        with gzip.open(packed,'rb') as stream:
            import hashlib
            digest=hashlib.sha256()
            for block in iter(lambda:stream.read(1024*1024),b''):
                digest.update(block)
        if digest.hexdigest()!=sha(raw):
            raise ValueError('artifact_roundtrip_failed')
        artifacts[run_label]=dict(raw_sha256=sha(raw),compressed_sha256=sha(packed),
                              raw_bytes=raw.stat().st_size,compressed_bytes=packed.stat().st_size)
    write(output/'raw-results-archive-manifest.json',artifacts)
    browser=ROOT/'var/m5-development/browser-v2/artifacts'
    write(output/'browser-result.json',json.loads((browser/'issue-12-result.json').read_text()))
    write(output/'browser-diagnostics.json',json.loads((browser/'diagnostics.json').read_text()))
    screenshot=browser/'m5-graph-timeline.png'
    (output/'m5-graph-timeline.png').write_bytes(screenshot.read_bytes())
    write(output/'sha256-manifest.json',{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps(dict(output=str(output),parity=sum(r['packet_equal'] for r in parity),archives=artifacts)))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery', default='delivery-v1')
    parser.add_argument('--label', default='delivery-analysis-v1')
    args = parser.parse_args()
    run(args.delivery, args.label)
