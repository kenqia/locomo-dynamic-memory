"""Prepare new immutable inputs; never execute or recover historical experiments."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from locomo_memory.raw_retrieval import pinned_sources
from locomo_memory.source_context import source_window

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'experiments/integration-acceptance-20261101'
WORKTREES = ROOT.parent
OLD = WORKTREES / 'top145-repair-context-20261030/experiments/top7-iteration-20261029'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


class ReadOnly:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path.as_uri() + '?mode=ro&immutable=1', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()


def main():
    builds = [
        ('conv-26', WORKTREES / 'current-showcase-five-strategies-frozen-20261021/memory.sqlite3', '5c7699dd6543407697ae232633154036'),
        ('conv-30', WORKTREES / 'dynamic-validation-20261027/var/dynamic-validation-32768-20261028/memory.sqlite3', '5abd7718841d417ebd71a1db896be39f'),
    ]
    pools = {}; provenance = []
    for sample, path, bid in builds:
        sources, snapshot = pinned_sources(ReadOnly(path), bid)
        pools[sample] = sources
        provenance.append(dict(sample_id=sample, path=str(path), database_sha256=digest(path), build_id=bid, snapshot=snapshot))
    data = json.loads((ROOT / 'data/raw/locomo/locomo10.json').read_text())
    cases = []; references = []
    # Official QA is a candidate reference only; independent source review precedes live calls.
    selection = {'conv-26': [5, 6, 10, 16, 20, 23], 'conv-30': [0, 1, 7, 13, 19, 20]}
    for sample, indices in selection.items():
        raw = next(c for c in data if c['sample_id'] == sample)
        by_dia = {s['dia_id']: s for s in pools[sample]}
        for i in indices:
            qa = raw['qa'][i]; cid = f'{sample}-official-{i:03d}'
            original = [by_dia[d] for d in qa['evidence']]
            sources, audit = source_window(pools[sample], original, radius=1, token_budget=24000)
            cases.append(dict(id=cid, cohort='existing-development-exposure-unknown', payload=dict(question=qa['question'], time=dict(cutoff=sources[-1]['session_time'], requested_date=None), status='sufficient', memories=[], sources=sources), source_selection=audit))
            references.append(dict(case_id=cid, question=qa['question'], candidate_official_answer=qa['answer'], facts=[dict(fact_id=cid+'-F1', claim=qa['answer'], evidence=original)], forbidden='Invented precision, event completion, changed actor, unsupported event identity, unsupported factual explanation or wrong refusal.', source='official QA candidate, independently verify before acceptance'))
    synthetic = [
        ('historical-state', 'Where did Ada live as of May 15, 2023?', [('Ada','2023-05-01T12:00:00','I live in Leeds.'),('Ada','2023-06-01T12:00:00','I moved to Oslo yesterday.')], 'Leeds, the latest time-eligible residence report.', '2023-05-15'),
        ('plan-not-done', 'Had Ben opened his cafe by June 19?', [('Ben','2023-06-19T12:00:00','My cafe opening is planned for June 25. It has not opened yet.')], 'Not yet as of June 19; the opening is planned for June 25.', '2023-06-19'),
        ('negative-polarity', 'Does Cora drink coffee?', [('Cora','2023-07-01T12:00:00','I do not drink coffee. I drink tea.')], 'Cora does not drink coffee.', None),
        ('unknown-exam', 'Which violin examination did Dan pass?', [('Dan','2023-07-01T12:00:00','I enjoy violin music. I have not mentioned taking or passing a violin examination.')], 'The evidence does not specify a passed exam. Empty insufficient answer is permitted; never infer no exam was ever passed.', None),
        ('event-identity', 'Did the interview and offer concern the same application?', [('Eva','2023-05-11T12:00:00','I interviewed for a design internship yesterday.'),('Eva','2023-05-27T12:00:00','I received a fashion internship offer today. I have not said whether it is the application I mentioned before.')], 'Same application is not established; neither definite identity nor definite distinctness is supported.', None),
        ('report-event-date', 'When did Finn move?', [('Finn','2023-06-02T12:00:00','I moved to York yesterday.')], 'June 1, 2023, rather than the June 2 report date.', None),
        ('two-jobs', 'What jobs does Gia hold?', [('Gia','2023-07-01T12:00:00','I work at a bank. I also opened a shop and still work at the bank.')], 'Both bank employment and the shop; opening the shop did not end the bank job.', None),
        ('missing-employer', 'Who is Hana employed by?', [('Hana','2023-07-01T12:00:00','I hope to become a counselor. I have not reported having a counseling job or named an employer.')], 'Employer unknown; aspiration does not establish employment or unemployment.', None),
        ('accepted-not-started', 'Has Ian started his internship?', [('Ian','2023-07-01T12:00:00','I accepted the internship offer yesterday. I start next Monday and have not started yet.')], 'Accepted June 30; not started as of July 1, planned next Monday.', None),
        ('collaborator', 'What did Jo paint and with whom?', [('Jo','2023-07-01T12:00:00','My children and I painted a mural inspired by nature.')], 'A nature-inspired mural with Jo\'s children.', None),
        ('two-facts', 'Which books did Kim read?', [('Kim','2023-07-01T12:00:00','I read Book A and Book B. I plan to read Book C.')], 'Book A and Book B, without presenting planned Book C as read.', None),
        ('beyond-cutoff', 'Where does Lee live as of 2025-01-01?', [('Lee','2023-07-01T12:00:00','I live in Bath. I have no information about my future residence in 2025.')], '2025 residence unknown; Bath is a 2023 report, not established 2025 reality.', '2025-01-01'),
    ]
    for name, question, turns, answer, date in synthetic:
        cid = 'synthetic-'+name
        sources = [dict(source_id=f'acceptance/{cid}/D1:{i+1}', dataset_id='acceptance', sample_id=cid, dia_id=f'D1:{i+1}', session_id=f'session_{i+1}', position=i, speaker=speaker, session_time=stamp, text=text) for i,(speaker,stamp,text) in enumerate(turns)]
        status = 'insufficient' if name in {'unknown-exam', 'missing-employer', 'beyond-cutoff'} else 'sufficient'
        cases.append(dict(id=cid, cohort='synthetic-boundary', payload=dict(question=question,time=dict(cutoff=turns[-1][1],requested_date=date,beyond_cutoff=name=='beyond-cutoff'),status=status,memories=[],sources=sources)))
        references.append(dict(case_id=cid, question=question, facts=[dict(fact_id=cid+'-F1',claim=answer,evidence=sources)], forbidden='Unsupported stronger assertion, invented exact date/actor, plan turned into completion, later fact used at earlier cutoff, unqualified future state.', source='new authored synthetic, requires independent acceptance'))
    old_tasks = json.loads((OLD / 'top145-next/windows/inputs.json').read_text())
    old_ref = json.loads((OLD / 'top145-open/answer-reference.json').read_text())
    for t in sorted([t for t in old_tasks if t['arm']=='w1' and t['repetition']==1],key=lambda t:t['case']):
        p = deepcopy(t['payload'])
        cases.append(dict(id=t['case'],cohort='known-four-regression',payload=p,build_id=t['build_id'], historical_input_source=str(OLD/'top145-next/windows/inputs.json')))
        ref=deepcopy(next(c for c in old_ref['cases'] if c['case_id']==t['case']))
        ref['facts']=ref.pop('required_facts'); references.append(ref)
    historical=[]
    roots=[WORKTREES/'extraction-anchor-feedback-20261028/experiments/conv30-ad-mini-20261028/execution-v1', WORKTREES/'resolution-contract-20261028/experiments/two-conversation-mini-20261028/execution']
    for root in roots:
        for path in sorted(root.glob('*-trace.json')):
            t=json.loads(path.read_text())
            if t.get('outcome')=='succeeded' and 'answer_input' in t:
                historical.append(dict(id=f'{root.parent.name}-{path.stem}',original_path=str(path),original_sha256=digest(path), resolution_input=t.get('resolution_input'),answer_input=t['answer_input'],historical_answer=t['answer'],config=t['config']))
    assert len(cases)==28 and len(historical)==10
    write(OUT/'cases.json',cases);write(OUT/'reference-candidates.json',references)
    write(OUT/'source-provenance.json',provenance);write(OUT/'historical-packets.json',historical)
    write(OUT/'scoring-protocol.json',dict(version='acceptance-v1',denominators=dict(reader_cases=28,repeats=2,arms=2,logical_outputs=112,historical_cases=10,budget_arms=2,historical_outputs=20),facts='For every required fact: covered/missing/incorrect/ambiguous. All answer, claims and explanation count; actual citation support checked against delivered text. Missing output remains not_evaluable in full denominator.',severe='Invented/contradictory actor, event identity, date, negation, plan/completion, employment status or cutoff; unsupported explanatory prose counts.',wrong_refusal='Omitted supported requested facts because of unnecessary insufficiency/refusal; necessary evidence-limited unknowns are correct.',uncertainty='Any unresolved reference dispute, unknown usage, unreviewed output or pending adjudication prevents semantic acceptance.',gates=dict(reader_real_gain_pp=10,fact_coverage_not_lower=True,new_severe=0,new_wrong_refusal=0,max_logical_pipeline_token_ratio=2.2,synthetic_no_regression=True,known_four_no_regression=True),limitations='Evidence-conditioned development experiment with oracle-selected official evidence ±1, not retrieval/end-to-end quality or hidden-set accuracy; real exposure unknown. Historical replay is generation-stage compatibility, not fresh full application run.'))
    print(json.dumps(dict(cases=28,historical=10,live_calls=0)))

if __name__=='__main__':main()
