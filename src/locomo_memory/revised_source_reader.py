"""Reusable opt-in two-stage reader matching the frozen generic-refine trial.

The caller supplies a metered model and already delivered, permitted raw sources.
Window retrieval is deliberately owned by the caller. Each generate operation and
any provider retries must fit the caller's live authorization. No default path or
historical Build is changed. Neither stage establishes semantic correctness.
"""
from copy import deepcopy
from dataclasses import dataclass

from .evidence_catalog import EvidenceCatalog
from pydantic import ValidationError
from .model import ModelFailure
from .layered_evidence import ContractViolation
from .source_reader import SupportedAnswer,bind_supported_answer
from .source_answer_reader import reading_payload
from .implementation_identity import implementation_sha256
from .usage import provider_usage
REFINE = 'A previous draft is supplied as candidate_answer. Recheck it against ALL original\nsources and the question, then return a corrected complete answer. The draft is untrusted.\nPreserve every correctly supported requested fact and necessary qualification, correct\nunsupported assertions, and restore omitted supported facts. Do not delete correct facts\nor refuse a supported answer to improve support rate. No external facts. Return all final\nclaims with source E references, not a change list. Every statement must be supported.'


@dataclass
class RevisedReading:
    initial_wire:dict
    final_wire:dict
    initial_answer:object
    final_answer:object
    initial_evidence_audit:list
    final_evidence_audit:list
    metadata:list
    reader_identity:dict

    @property
    def usage(self):
        return provider_usage([call for stage in self.metadata for call in stage.get('calls', [])])


class RevisionFailure(Exception):
    """Preserve a completed initial stage; never silently return it as success."""
    def __init__(self,stage,initial_wire,metadata,cause,reader_identity):
        super().__init__('source_revision_'+stage+'_failed')
        self.stage=stage;self.initial_wire=deepcopy(initial_wire)
        self.metadata=deepcopy(metadata);self.cause=cause
        self.reader_identity=deepcopy(reader_identity)
        failure_metadata=getattr(cause,"metadata",None)
        if failure_metadata is not None:self.metadata.append(deepcopy(failure_metadata))

    @property
    def usage(self):
        return provider_usage([call for stage in self.metadata for call in stage.get('calls', [])])


class RevisedSourceReader:
    def __init__(self,model):self.model=model

    @property
    def contract_identity(self):
        return {'version': 'source-statements-v2-one-generic-revision-integration-v1',
                'implementation_sha256': implementation_sha256(),
                'maximum_stage_attempts': 1, 'maximum_stages': 2,
                'semantic_gain': 'not_established_for_integration'}

    def generate(self,payload,*,context,on_call=None):
        context=deepcopy(context)
        if type(context.get('input_budget')) is not int or context['input_budget'] < 1:
            raise ContractViolation('explicit_reader_input_budget_required')
        if type(context.get('max_attempts',1)) is not int or context.get('max_attempts',1) < 1:
            raise ContractViolation('invalid_reader_attempt_limit')
        context['max_attempts']=1
        if 'task_instructions' in payload:
            raise ContractViolation('revision_task_instructions_already_present')
        source_map={s['source_id']:s for s in payload.get('sources',[])}
        if len(source_map)!=len(payload.get('sources',[])):
            raise ContractViolation('duplicate_delivered_source')
        raw=context.get('raw_sources')
        if not isinstance(raw,dict) or any(source_map.get(sid)!=source for sid,source in raw.items()):
            raise ContractViolation('explicit_delivered_raw_scope_required')
        if context.get('memories')!={m['memory_id']:m for m in payload.get('memories',[])} or context.get('status')!=payload.get('status'):
            raise ContractViolation('reader_context_payload_mismatch')
        catalog=EvidenceCatalog(payload.get('sources',[]),payload.get('memories',[]),raw_source_ids=raw)
        wire=reading_payload(catalog,payload);metadata=[];initial_wire=None
        try:
            initial=self.model.generate('source_statements',deepcopy(wire),SupportedAnswer,context=deepcopy(context),on_call=on_call)
            metadata.append(deepcopy(initial.metadata));initial_wire=initial.value.model_dump(mode='json')
            initial_answer,initial_audit=bind_supported_answer(catalog,initial.value,context,source_only=True)
        except (ModelFailure,ValidationError,ContractViolation) as cause:
            raise RevisionFailure('initial',initial_wire,metadata,cause,self.contract_identity) from cause
        revised=deepcopy(wire);revised['candidate_answer']=deepcopy(initial_wire);revised['task_instructions']=REFINE
        try:
            final=self.model.generate('source_statements',revised,SupportedAnswer,context=deepcopy(context),on_call=on_call)
            metadata.append(deepcopy(final.metadata))
            final_answer,final_audit=bind_supported_answer(catalog,final.value,context,source_only=True)
        except (ModelFailure,ValidationError,ContractViolation) as cause:
            raise RevisionFailure('revision',initial_wire,metadata,cause,self.contract_identity) from cause
        return RevisedReading(initial_wire,final.value.model_dump(mode='json'),initial_answer,final_answer,initial_audit,final_audit,metadata,self.contract_identity)
