"""Repack saved successful business inputs, without generating a new answer.

Checks whole Memory semantic values and original source text, not just source IDs.
This is deterministic delivery compatibility, never a new semantic/model score.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from locomo_memory.config import Settings
from locomo_memory.model import Generation
from locomo_memory.query_payload import query_wire_payload
from locomo_memory.queries import QueryService
# Reproduce the rejected policy, not the repaired current raw-only packer.
import subprocess
import sys
from types import ModuleType
CORE = 'c156a1d9cf344a06c9d4d0d7f9f97e39242277f7'
ROOT = Path(__file__).resolve().parents[2]
old = ModuleType('locomo_memory._rejected_packing')
old.__package__ = 'locomo_memory'
sys.modules[old.__name__] = old
source = subprocess.check_output(['git', 'show', CORE + ':src/locomo_memory/raw_queries.py'], cwd=ROOT, text=True)
exec(compile(source, old.__name__, 'exec'), old.__dict__)
pack_payload = old.pack_payload

R = Path('/home/kenqia/my_folder/locomo-worktrees')
roots = [R / 'extraction-anchor-feedback-20261028/experiments/conv30-ad-mini-20261028/execution-v1',
         R / 'resolution-contract-20261028/experiments/two-conversation-mini-20261028/execution']
# Accepted by the original independent human reviews; disputed/missing-source
# packets and unreviewed/failed outputs are not reclassified as accepted.
accepted = {'01-A-trace.json', '01-D-trace.json', '10-D-trace.json',
            'conv-26-mini-01-A-trace.json', 'conv-26-mini-01-D-trace.json', 'conv-26-mini-02-D-trace.json'}
rows = []
for root in roots:
    for path in sorted(root.glob('*-trace.json')):
        trace = json.loads(path.read_text())
        if trace.get('outcome') != 'succeeded' or 'answer_input' not in trace:
            continue
        payload = trace['answer_input']; settings = Settings.model_validate(trace['config'])
        expected = deepcopy(trace['answer'])
        captured = {}
        class Replay:
            def generate(self, operation, wire, schema, *, context):
                captured.update(deepcopy(wire))
                return Generation(schema.model_validate(deepcopy(expected), context=context), {'calls': []})
        service = SimpleNamespace(settings=settings, model=Replay())
        QueryService.generate_answer(service, payload['question'], payload['time'], payload['memories'],
                                     {s['source_id']:s for s in payload['sources']}, payload['status'])
        before = query_wire_payload('answer', payload)
        after = query_wire_payload('answer', captured)
        delivered_m = {m['memory_id']:m for m in after['memories']}
        delivered_s = {s['source_id']:s for s in after['sources']}
        assert all(delivered_m.get(m['memory_id']) == m for m in before['memories'])
        assert all(delivered_s.get(s['source_id']) == s for s in before['sources'])
        resolution = trace.get('resolution_input')
        missing = []
        preserved = []
        if resolution:
            source_map = {s['source_id']:s for s in resolution['sources']}
            packed, audit = pack_payload({**resolution, 'operation':'resolve'}, resolution['memories'], [], source_map, settings)
            wire = query_wire_payload('resolve', packed)
            supplied = {m['memory_id']:m for m in wire['memories']}
            originals = {m['memory_id']:m for m in query_wire_payload('resolve', resolution)['memories']}
            selected = set(trace.get('resolution_selected_memory_ids', []))
            missing = sorted(selected - supplied.keys())
            for mid in sorted(selected & supplied.keys()):
                assert supplied[mid] == originals[mid]
                assert all(source_map[sid] in packed['sources'] for sid in supplied[mid]['source_ids'])
                preserved.append({'memory_id':mid, 'semantic_fields_sha256':hashlib.sha256(json.dumps(supplied[mid],sort_keys=True).encode()).hexdigest()})
        rows.append({'trace':str(path), 'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'historically_human_accepted':path.name in accepted,
                     'whole_delivered_memory_values_and_source_text_preserved':True,
                     'old_selected_missing_from_new_resolution_input':missing,
                     'old_selected_semantic_objects_preserved':preserved})
assert len(rows) == 10
blocking = [r for r in rows if r['historically_human_accepted'] and r['old_selected_missing_from_new_resolution_input']]
result = {'saved_successful_traces_replayed':len(rows), 'historically_human_accepted_traces':sum(r['historically_human_accepted'] for r in rows),
          'blocking_old_accepted_delivery_losses':len(blocking), 'results':rows,
          'live_calls':0, 'new_semantic_or_accuracy_result':False,
          'limitation':'Original Memory values and raw source text retained for these saved successful packets; does not establish behavior of a new model output or completeness outside these packets.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(1 if blocking else 0)
