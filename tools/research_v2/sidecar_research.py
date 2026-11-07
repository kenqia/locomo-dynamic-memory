"""ARCH-03 independent diagnostic decorator. Never changes production results.

This is an optional consumer of an already-produced response and snapshot, not
an HTTP route or a provider. Production does not import this module.
"""
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Literal
from tools.research_v2.sidecar_core import diagnose, SidecarDiagnostics
from tools.research_v2.sidecar_schema import SidecarInput

RESEARCH_VERSION='sidecar-research-v0.4-research'


def canonical_bytes(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class ResearchView:
    response: Any
    status: Literal['disabled','diagnosed','diagnostic_failed']
    diagnostic: SidecarDiagnostics | None = None
    error_code: str | None = None


def research_view(response, snapshot=None, *, enabled=False, max_event_pairs=1000):
    """Return original response by identity. Annotation is out-of-band.

    Disabled exits before parsing snapshot or running diagnostics. Enabled failures preserve the original response too.
    This alone makes no assertion about a production HTTP endpoint, which is
    deliberately not connected in ARCH-03.
    """
    if type(enabled) is not bool:
        raise TypeError('enabled must be explicit boolean')
    if not enabled:
        return ResearchView(response=response,status='disabled')
    try:
        validated=snapshot if isinstance(snapshot,SidecarInput) else SidecarInput.model_validate(snapshot)
        if isinstance(response,dict):
            p=validated.provenance
            scope={'build_id':p.build_id,'dataset_id':p.dataset_id,'sample_id':p.sample_id,'build_fingerprint':p.build_fingerprint}
            if any(k in response and response[k]!=v for k,v in scope.items()):
                raise ValueError('Original response and diagnostic snapshot scopes differ')
        value=diagnose(validated,enabled=True,max_event_pairs=max_event_pairs)
        return ResearchView(response=response,status='diagnosed',diagnostic=value)
    except Exception:
        # Do not emit snapshot text, model errors or credentials in error details.
        return ResearchView(response=response,status='diagnostic_failed',error_code='sidecar_diagnostic_failed')


def baseline_fields(snapshot:SidecarInput):
    """Control: inspect supplied fields only; do not parse time or resolve state.

    Not the real production QA baseline. Unknown reflects missing supplied
    structured fields, not proof the source lacks an answer.
    """
    sources={s.source_id:s for s in snapshot.sources}
    return {'variant':'supplied_fields_only','inference':False,
        'claims':[{'memory_id':c.memory_id,'source_ids':list(c.source_ids),
                   'reported_at':[sources[sid].reported_at.isoformat() for sid in c.source_ids],
                   'event_time':c.event_time.model_dump(mode='json'),
                   'statement_type':c.statement_type,'polarity':c.polarity,
                   'completed':'unknown','attended':'unknown'} for c in snapshot.claims],
        'event_links':[],'query':None,
        'retained_memory_ids':[c.memory_id for c in snapshot.claims]}


def off_on_off(snapshot):
    """Preserve an explicitly synthetic input echo, not an invented QA answer."""
    original={'kind':'SYNTHETIC_INPUT_ECHO_NOT_QA','input':snapshot.model_dump(mode='json')}
    before=canonical_bytes(original)
    off=research_view(original,snapshot)
    on=research_view(original,snapshot,enabled=True)
    rollback=research_view(original,snapshot,enabled=False)
    unchanged=(off.response is original and on.response is original and rollback.response is original
               and canonical_bytes(original)==before)
    return {'input_echo_only':True,'response_identity_unchanged':unchanged,
        'response_sha256_before':hashlib.sha256(before).hexdigest(),
        'response_sha256_after':digest(original),
        'statuses':[off.status,on.status,rollback.status],
        'rollback_has_no_diagnostic':rollback.diagnostic is None,
        'production_query_hook':False}
