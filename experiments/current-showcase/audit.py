"""Read-only final consistency and budget checks for the completed experiment."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).parent))
import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory', required=True, type=Path)
parser.add_argument('--results', required=True, type=Path)
args = parser.parse_args()
directory, output = args.directory.resolve(), args.results.resolve()
plan = json.loads((directory / 'plan.json').read_text())
outcome = json.loads((directory / 'outcome.json').read_text())
with sqlite3.connect((directory / 'campaign.sqlite3').as_uri()+'?mode=ro', uri=True) as db:
    calls = [json.loads(r[0]) for r in db.execute('SELECT metadata FROM calls ORDER BY sequence')]
artifact_digest = run.live.previous.previous.artifact_digest
checks = dict(
    completed=outcome['status'] == 'completed',
    plan_digest=run.live.digest(directory / 'plan.json') == (directory / 'plan.sha256').read_text().strip(),
    frozen_runner=run.live.digest(Path(run.__file__)) == plan['runner_sha256'],
    frozen_helpers=all(run.live.digest(Path(p)) == h for p,h in plan['helper_sha256'].items()),
    frozen_implementation=run.implementation_sha256() == plan['implementation_sha256'],
    prior_ledger_unchanged=run.live.digest(run.PRIOR) == plan['prior_ledger_sha256'],
    source_build_unchanged=artifact_digest(run.SOURCE / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'],
    snapshot_build_unchanged=artifact_digest(directory / 'memory.sqlite3') == plan['immutable_build_artifacts_sha256'],
    source_turns_unchanged=run.live.digest(directory / 'source-turns.json') == plan['source_turns_sha256'],
    all_calls_completed=all(c.get('completed_at') for c in calls),
    ledger_matches_outcome=len(calls) == outcome['budget_after']['reserved_new_calls'],
    within_authorization=len(calls) <= plan['call_limit'],
    within_cumulative_limit=plan['previous_calls']+len(calls) <= plan['cumulative_ceiling'])
paired = json.loads((output / 'paired-results.json').read_text())
rows = paired['rows']
checks['paired_100_unique'] = len(rows) == len({(r['qa_index'],r['strategy']) for r in rows}) == 100
checks['paired_success'] = all(r['status'] == 'succeeded' for r in rows)
recall = json.loads((output / 'recall-results.json').read_text())
checks['recall_40_completed'] = recall['summary']['completed'] == recall['summary']['planned'] == 40
with (output / 'paired-differences.csv').open() as f:
    checks['csv_20_questions'] = len(list(csv.DictReader(f))) == 20
for name, count in [('answer-source-review',20), ('dynamic-review',10)]:
    review = json.loads((output / f'{name}.json').read_text())
    checks[f'{name}_complete'] = len(review['records']) == count
    packets = json.loads((output / ('answer-source-packets.json' if count == 20 else 'dynamic-packets.json')).read_text())
    packet_by_trace = {p['trace_id']: p for p in packets}
    checks[f'{name}_answer_binding'] = all(
        r['trace_id'] in packet_by_trace and r['answer_sha256'] == hashlib.sha256(
            (packet_by_trace[r['trace_id']]['answer'] if count == 20 else
             packet_by_trace[r['trace_id']]['answer']['answer']).encode()).hexdigest()
        for r in review['records'])
web = json.loads((output.parent / 'web-recorded/results.json').read_text())
checks['web_five_passed'] = len(web['scenarios']) == 5 and all(r['status']=='passed' for r in web['scenarios'])
checks['web_no_errors'] = not web['pageerrors'] and not web['console_errors']
summary = dict(checks=checks, all_passed=all(checks.values()), new_calls=len(calls),
    cumulative_calls=plan['previous_calls']+len(calls),
    call_outcomes=dict(Counter(c.get('outcome','unknown') for c in calls)),
    usage=outcome['budget_after']['usage'],
    limitation='Checks read saved results, identities and the ledger; they do not judge answer semantics or issue new provider calls.')
(output / 'final-audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(dict(all_passed=summary['all_passed'], checks=checks, new_calls=len(calls))))
assert summary['all_passed']
