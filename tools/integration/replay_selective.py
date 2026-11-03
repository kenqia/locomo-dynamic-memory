"""Read frozen narrow-context tasks and check exact source/wire compatibility."""
import json
from pathlib import Path
from locomo_memory.selective_context import predecessor_context
from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.source_answer_reader import reading_payload

ROOT = Path('/home/kenqia/my_folder/locomo-worktrees/top145-repair-context-20261030/experiments/top7-iteration-20261029')
old = json.loads((ROOT / 'top145-next/windows/inputs.json').read_text())
new = json.loads((ROOT / 'top145-repair-context/context-initial/inputs.json').read_text())
count = 0
for task in new:
    if task['arm'] != 'narrow':
        continue
    pair = [t for t in old if t['case'] == task['case'] and t['repetition'] == task['repetition']]
    original = next(t for t in pair if t['arm'] == 'w0')['payload']['sources']
    expanded = next(t for t in pair if t['arm'] == 'w1')['payload']['sources']
    sources, audit = predecessor_context(original, expanded)
    assert sources == task['payload']['sources'] and not audit['truncated']
    catalog = EvidenceCatalog(sources, task['payload'].get('memories', []), raw_source_ids=task['context']['raw_sources'])
    assert reading_payload(catalog, task['payload']) == task['wire_payload']
    count += 1
assert count == 8
print(json.dumps(dict(source_commit='250795a', frozen_tasks_replayed=count,
                     source_and_wire_changes=0, semantic_results_inherited=False, live_calls=0), indent=2))
