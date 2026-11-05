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
from locomo_memory.resolution_delivery import complete_resolution_input

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
            original_context, audit = complete_resolution_input(resolution, settings)
            wire = query_wire_payload('resolve', resolution)
            supplied = {m['memory_id']:m for m in wire['memories']}
            originals = {m['memory_id']:m for m in query_wire_payload('resolve', resolution)['memories']}
            selected = set(trace.get('resolution_selected_memory_ids', []))
            missing = sorted(selected - supplied.keys())
            for mid in sorted(selected & supplied.keys()):
                assert supplied[mid] == originals[mid]
                assert all(source_map[sid] in resolution['sources'] for sid in supplied[mid]['source_ids'])
                preserved.append({'memory_id':mid, 'semantic_fields_sha256':hashlib.sha256(json.dumps(supplied[mid],sort_keys=True).encode()).hexdigest()})
        rows.append({'trace':str(path), 'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'historically_human_accepted':path.name in accepted,
                     'whole_delivered_memory_values_and_source_text_preserved':True,
                     'old_selected_missing_from_new_resolution_input':missing,
                     'old_selected_semantic_objects_preserved':preserved,
                     'original_complete_input_token_count':audit['input_token_count'] if resolution else None,
                     'original_packet_exceeds_default_input_budget':not audit['within_budget'] if resolution else False})
assert len(rows) == 10
blocking = [r for r in rows if r['historically_human_accepted'] and r['old_selected_missing_from_new_resolution_input']]
result = {'saved_successful_traces_replayed':len(rows), 'historically_human_accepted_traces':sum(r['historically_human_accepted'] for r in rows),
          'blocking_old_accepted_delivery_losses':len(blocking),
          'saved_resolution_packets_rejected_before_resolve_http_at_default_budget':sum(r['original_packet_exceeds_default_input_budget'] for r in rows),
          'results':rows,
          'live_calls':0, 'new_semantic_or_accuracy_result':False,
          'limitation':'Complete packets and all Memory values/source text remain intact. Oversized saved resolution packets explicitly fail before resolution HTTP at default budget; this is not restored technical completion. These historical ablation packets are not a new default API run or semantic score.'}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(1 if blocking else 0)
