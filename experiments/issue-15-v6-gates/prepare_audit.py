"""Freeze a risk-focused semantic sample without further model generation."""
import hashlib
import json
from pathlib import Path
import re

from locomo_memory.experiment import write_json
from locomo_memory.relation_replay import comparison, source_snapshot
from locomo_memory.relation_schemas import relation_label_error
from gates import SOURCE, BUILD


def prepare(directory):
    state = json.loads((directory/'gates.json').read_text())
    assert state['gate4']['status'] == 'passed'
    target = directory/'audit-inputs.json'
    if target.exists():
        raise ValueError('audit_sample_already_frozen')
    reports = [json.loads((directory/name).read_text()) for name in ('lengths-after-balance.json', 'evidence.json')]
    selected, controls, strata = [], [], []
    with source_snapshot(SOURCE) as (db, source_hash):
        for report in reports:
            for attempt in report['attempts']:
                if attempt.get('max_tokens', report.get('max_tokens')) != 8192:
                    continue
                ordinal = int(attempt['source_task_id'].rsplit(':', 1)[1])
                identity, _, context = comparison(db, BUILD, ordinal)
                old_by_id = {old['memory_id']: old for old in context['history']}
                cases = []
                for judgment in attempt['judgments']:
                    old, new = old_by_id[judgment['old_memory_id']], context['new_memory']
                    ids = sorted(set(old['source_ids'] + new['source_ids']))
                    words = lambda text: set(re.findall(r'[a-z]+', text.lower())) - {'the','a','an','to','in','of','and','is','has','was','her','his'}
                    overlap = len(words(old['content']) & words(new['content']))
                    case = {'source_task_id': identity['task_id'], 'old_memory': old, 'new_memory': new,
                            'judgment': judgment, 'same_state_key': old['state_key'] == new['state_key'],
                            'lexical_overlap': overlap,
                            'allowed_labels': [label for label in ('RETAIN','UPDATE','SUPERSEDE','CONFLICT','undetermined')
                                               if relation_label_error(label, old, new) is None],
                            'sources': [context['sources'][s] for s in ids]}
                    (cases if judgment['label']=='undetermined' else controls).append(case)
                cases.sort(key=lambda c: (not c['same_state_key'], -c['lexical_overlap'],
                           hashlib.sha256(c['old_memory']['memory_id'].encode()).hexdigest()))
                chosen = cases[:6]
                selected.extend(chosen)
                strata.append({'task_ordinal': ordinal,'available_undetermined':len(cases),
                               'same_state_key_available':sum(c['same_state_key'] for c in cases),
                               'selected':len(chosen),'same_state_key_selected':sum(c['same_state_key'] for c in chosen)})
    packet = {'source_sha256':source_hash,'scope':'24 risk-focused undetermined comparisons + determined controls',
              'selection':'Per task, same_state_key first, then descending lexical overlap; stable SHA-256 tie-break; six per task.',
              'new_deepseek_calls':0,'not_human_ground_truth':True,'strata':strata,
              'undetermined_cases':selected,'determined_controls':controls}
    assert len(selected)==24 and len(controls)==2
    write_json(target,packet)
    print(json.dumps({'strata':strata,'undetermined_sample':len(selected),'controls':len(controls)}))


if __name__=='__main__':
    prepare(Path('/home/kenqia/my_folder/locomo-worktrees/real-baseline-issue15-relations-v6'))
