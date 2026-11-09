"""Offline JSON snapshot adapter and exclusive Sidecar writer.

Never opens a database or starts an API/provider. Treat an existing complete
export as read-only input; use an isolated directory for diagnostic outputs.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from locomo_memory.temporal import session_datetime
from tools.research_v2.sidecar_schema import (
    Provenance, SidecarInput, SourceEvidence, StateClaim, TimeInterval,
)
from tools.research_v2.sidecar_core import RULE_VERSION, diagnose

MAX_INPUT_BYTES = 20 * 1024 * 1024

def read_frozen(path: Path):
    path=Path(path)
    with path.open('rb') as handle:
        data=handle.read(MAX_INPUT_BYTES+1)
    if len(data)>MAX_INPUT_BYTES:raise ValueError('Input exceeds bounded offline snapshot limit')
    return data,hashlib.sha256(data).hexdigest()


def input_from_export(payload, *, origin):
    """Map validated, pinned production MemoryExport into diagnostic contract.

    Build fingerprint is copied, not recalculated from this reduced sidecar.
    Event-time intervals are read as proposals and rechecked against source text.
    No old relation is taken as proof that its label is semantically correct.
    """
    from locomo_memory.export_schemas import MemoryExport
    bundle=MemoryExport.model_validate(payload)
    source_models=tuple(SourceEvidence(source_id=s.source_id,session_id=s.session_id,
        turn_id=s.dia_id,speaker=s.speaker,reported_at=session_datetime(s.session_time),text=s.text)
        for s in bundle.sources)
    claims=[]
    for m in bundle.memories:
        t=m.time
        interval=TimeInterval(original_expression=t.original_expression,
            anchor_source_id=t.anchor_source_id,basis='Preserved extracted proposal; core rechecks source expression.')
        claims.append(StateClaim(memory_id=m.memory_id,entity_id=m.entity_id,
            state_dimension=m.state_dimension,state_value=m.state_value,content=m.content,
            memory_type=m.memory_type,statement_type=m.statement_type,polarity=m.polarity,
            source_ids=tuple(m.source_ids),event_time=interval))
    return SidecarInput(provenance=Provenance(dataset_id=bundle.build.dataset_id,
        sample_id=bundle.build.sample_id,build_id=bundle.build.build_id,
        build_fingerprint=bundle.build.fingerprint,rule_version=RULE_VERSION,origin=origin),
        sources=source_models,claims=tuple(claims))


def diagnose_file(input_path,output_path,*,enabled=False,format='snapshot',origin=None,
                  question=None,as_of=None,max_event_pairs=1000):
    """Save to a NEW file; never overwrite input, an existing output or symlink.

    Raw file SHA before/after detects change; no guarantee against a concurrent
    uncooperative writer after the final check. Use frozen exports, not live DBs.
    """
    inp,out=Path(input_path).resolve(strict=True),Path(output_path)
    if out.exists() or out.is_symlink() or out.resolve()==inp:
        raise ValueError('Output must be a new independent file')
    before,digest=read_frozen(inp)
    payload=json.loads(before)
    if format=='snapshot':
        snapshot=SidecarInput.model_validate(payload)
    elif format=='export':
        if origin not in ('synthetic','source_snapshot'):raise ValueError('Explicit export origin required')
        snapshot=input_from_export(payload,origin=origin)
    else:raise ValueError('Unsupported input format')
    if question is not None or as_of is not None:
        data=snapshot.model_dump(mode='json')
        if question is not None:data['question']=question
        if as_of is not None:data['as_of']=as_of
        snapshot=SidecarInput.model_validate(data)
    result=diagnose(snapshot,enabled=enabled,max_event_pairs=max_event_pairs)
    _,after_digest=read_frozen(inp)
    if digest!=after_digest:raise ValueError('Input changed while reading; diagnostic discarded')
    output={'input_sha256_before':digest,'input_sha256_after':after_digest,
            'input_unchanged':True,'diagnostic':result.model_dump(mode='json')}
    # Exclusive create also prevents races with another diagnostic writer.
    encoded=(json.dumps(output,ensure_ascii=False,indent=2)+'\n').encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as handle:
        handle.write(encoded)
    return output
