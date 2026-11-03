"""Bounded extraction address repair and deterministic predecessor context selection."""
from copy import deepcopy
from typing import Literal
from pydantic import Field,StrictInt,StrictStr
from .layered_contracts import Contract
from .layered_evidence import ContractViolation
from .proposition_extraction import bind_proposition

class AddressPatch(Contract):
    index:StrictInt=Field(ge=0)
    evidence_refs:list[StrictStr]=Field(min_length=1)
    time_refs:list[StrictStr]=Field(default_factory=list)

class PatchBatch(Contract):
    status:Literal['corrected','unsupported']
    patches:list[AddressPatch]


def validate_records(catalog,records):
    accepted=[];failures=[]
    for index,record in enumerate(records):
        try:
            m,a=bind_proposition(catalog,record);accepted.append({'index':index,'memory':m.model_dump(mode='json'),'audit':a})
        except (ValueError,TypeError):failures.append(index)
    return accepted,failures


def apply_patches(catalog,records,value):
    patch=PatchBatch.model_validate(value);_,failed=validate_records(catalog,records)
    indices=[p.index for p in patch.patches]
    if not failed:
        if indices:raise ContractViolation('repair_of_valid_batch_forbidden')
        return deepcopy(records)
    if patch.status!='corrected':raise ContractViolation('atomic_repair_unsupported')
    if len(indices)!=len(set(indices)) or set(indices)!=set(failed):raise ContractViolation('repair_scope_mismatch')
    revised=deepcopy(records)
    for p in patch.patches:
        original=records[p.index]
        # Existing recognized time wording and session anchor must survive.
        signature=lambda refs:sorted((catalog.times[r]['text'],catalog.sources[catalog.times[r]['source_id']]['session_time']) for r in refs if r in catalog.times)
        before=signature(original.get('time_refs',[]));after=signature(p.time_refs)
        if before!=after:raise ContractViolation('repair_time_meaning_changed')
        if original.get('time_refs') and not p.time_refs:raise ContractViolation('repair_time_dropped')
        revised[p.index].update(evidence_refs=p.evidence_refs,time_refs=p.time_refs)
    _,failures=validate_records(catalog,revised)
    if failures:raise ContractViolation('repair_still_invalid')
    return revised

