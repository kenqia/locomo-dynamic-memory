from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.research_v2.phase3_screening import frozen_producer, select_samples
from tools.research_v2.phase3_regression import wire_payload
from tools.research_v2.postbaseline import sha


def population():
    rows=[]
    for sid in ('conv-26','conv-30','conv-41','conv-42'):
        for category in ('1','2','3','4','5'):
            if sid=='conv-30' and category=='3':continue
            rows.extend(dict(question_id=f'{sid}:{category}:{i}',conversation=sid,category=category,qa=0) for i in range(10))
    return rows


def test_frozen_strata_preserve_every_existing_category_and_never_invent_one():
    rows=population();excluded={r['question_id'] for r in rows[::4]}
    selected=select_samples(rows,excluded)
    assert len(selected)==48
    assert not {r['question_id'] for r in selected}&excluded
    for sid in ('conv-26','conv-30','conv-41','conv-42'):
        assert sum(r['conversation']==sid for r in selected)==12
        assert {r['category'] for r in selected if r['conversation']==sid}=={r['category'] for r in rows if r['conversation']==sid}


def test_selection_ignores_scores_outcomes_and_input_order():
    rows=population();expected=[r['question_id'] for r in select_samples(rows,set())]
    changed=deepcopy(rows)[::-1]
    for r in changed:r.update(qa=1,failed=True,answer='do not select using me')
    assert [r['question_id'] for r in select_samples(changed,set())]==expected


def test_missing_real_category_is_a_hard_freeze_failure():
    rows=population();excluded={r['question_id'] for r in rows if r['conversation']=='conv-30' and r['category']=='4'}
    with pytest.raises(ValueError,match='category'):select_samples(rows,excluded)


def test_saved_wire_hash_must_match_and_path_cannot_escape(tmp_path):
    observer=tmp_path/'observer';observer.mkdir()
    raw=json.dumps(dict(messages=[dict(content='system'),dict(content=json.dumps(dict(question='Synthetic question')))])).encode()
    (observer/'test.request.json').write_bytes(raw)
    record=dict(wire_path='test.request.json',request_sha256=sha(raw))
    assert wire_payload(tmp_path,record)==dict(question='Synthetic question')
    with pytest.raises(ValueError,match='changed'):wire_payload(tmp_path,{**record,'request_sha256':'wrong'})
    with pytest.raises(ValueError,match='escapes'):wire_payload(tmp_path,{**record,'wire_path':'../other.json'})


def test_real_pair_artifact_is_complete_unique_and_keeps_unknowns():
    root=Path(__file__).resolve().parents[1]
    rows=json.loads((root/'experiments/research-v2/phase3/paired-items.json').read_text())
    assert len(rows)==len({r['question_id'] for r in rows})==757
    assert sum(r['pair_state']=='unknown' for r in rows)==1
    assert sum(r['delta_dynamic_minus_hybrid'] is not None for r in rows)==705
    assert all(r['hybrid']['build_id']==r['dynamic']['build_id'] for r in rows)


def test_coordinator_execution_identity_is_hash_bound_and_uses_archived_contracts(tmp_path):
    import hashlib
    from locomo_memory.model import ANSWER_PROMPT, QUERY_ANALYSIS_PROMPT, RESOLUTION_PROMPT
    from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
    from locomo_memory.retrieval_schemas import QueryAnalysis
    contracts={stage:dict(prompt_sha256=sha(prompt.encode()),schema_sha256=sha(json.dumps(schema.model_json_schema(),sort_keys=True).encode()))
               for stage,prompt,schema in [('Query Analysis',QUERY_ANALYSIS_PROMPT,QueryAnalysis),
                   ('Resolution',RESOLUTION_PROMPT,EffectiveResolution),('Answer',ANSWER_PROMPT,EvidenceAnswer)]}
    p=tmp_path/'execution-identity.json';p.write_text(json.dumps(dict(stage_contracts=contracts)))
    meta=dict(execution_identity_sha256=sha(p.read_bytes()))
    result=frozen_producer(tmp_path,meta)
    assert result['stage_contracts']==contracts
    with pytest.raises(ValueError,match='identity'):frozen_producer(tmp_path,dict(execution_identity_sha256='wrong'))
    contracts['Answer']['prompt_sha256']='changed';p.write_text(json.dumps(dict(stage_contracts=contracts)))
    with pytest.raises(ValueError,match='contract'):frozen_producer(tmp_path,dict(execution_identity_sha256=sha(p.read_bytes())))
