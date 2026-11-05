"""Optional lossless wire grouping, after production source packing and validation.

The transport preserves every Memory field and source. Decoder guidance is counted;
if the complete request grows, the original request is sent unchanged.
"""
import json

import httpx

from .imports import canonical_json
from .model import DeepSeekModel, Generation
from .retrieval import budget_tokens

GUIDANCE = (
    '\nInput memory_groups_v1 is a lossless encoding of the memories array. '
    'For each group, reconstruct each memory by merging shared with each member; '
    'members contain no shared keys. memory_order contains [group_index,member_index] '
    'pairs giving the original ranking. Every reconstructed memory keeps its own '
    'memory_id, sources, time, polarity, and statement_type. Group membership is '
    'not evidence of event identity, contradiction, or current validity. '
    'Use original memory_id and source_ids in output; all other rules still apply.'
)


def group_wire(memories):
    groups, positions, order = [], {}, []
    for memory in memories:
        shared = {key: memory[key] for key in ('entity_id', 'state_dimension', 'state_key') if key in memory}
        key = canonical_json(shared)
        if key not in positions:
            positions[key] = len(groups)
            groups.append(dict(shared=shared, members=[]))
        index = positions[key]
        order.append([index, len(groups[index]['members'])])
        groups[index]['members'].append({k: v for k, v in memory.items() if k not in shared})
    return dict(memory_groups_v1=groups, memory_order=order)


def ungroup_wire(encoded):
    groups = encoded['memory_groups_v1']
    expected = {(i, j) for i, group in enumerate(groups) for j in range(len(group['members']))}
    order = [tuple(pair) for pair in encoded['memory_order']]
    if len(order) != len(set(order)) or set(order) != expected:
        raise ValueError('wire_compression_order_invalid')
    if any(set(group['shared']) & set(member) for group in groups for member in group['members']):
        raise ValueError('wire_compression_shared_override')
    return [{**groups[i]['shared'], **groups[i]['members'][j]} for i, j in order]


def encode_request(body):
    """Return body + actual complete-message proxy counts; no provider token claim."""
    original = budget_tokens(json.dumps(body['messages'], ensure_ascii=False))
    payload = json.loads(body['messages'][1]['content'])
    audit = dict(version='m5-wire-grouping-v1', original_message_tokens=original,
                 sent_message_tokens=original, applied=False, method='regex-word-punctuation-v1')
    if payload.get('operation') not in ('answer', 'resolve') or not payload.get('memories'):
        audit['reason'] = 'operation_or_empty_memories'
        return body, audit
    encoded = group_wire(payload['memories'])
    if ungroup_wire(encoded) != payload['memories']:
        raise ValueError('wire_compression_roundtrip_failed')
    candidate = json.loads(json.dumps(body))
    del payload['memories']
    payload.update(encoded)
    candidate['messages'][0]['content'] += GUIDANCE
    candidate['messages'][1]['content'] = json.dumps(payload, ensure_ascii=False)
    count = budget_tokens(json.dumps(candidate['messages'], ensure_ascii=False))
    audit.update(candidate_message_tokens=count, roundtrip=True)
    if count >= original:
        audit['reason'] = 'decoder_overhead_exceeds_savings'
        return body, audit
    audit.update(sent_message_tokens=count, applied=True, reason='complete_request_is_smaller')
    return candidate, audit


class CompressionTransport(httpx.BaseTransport):
    def __init__(self, delegate):
        self.delegate, self.audits = delegate, []

    def handle_request(self, request):
        body, audit = encode_request(json.loads(request.content))
        self.audits.append(audit)
        content = json.dumps(body, ensure_ascii=False).encode()
        # Preserve header values in memory only. No credential/header logging.
        headers = [(key, value) for key, value in request.headers.multi_items() if key.lower() != 'content-length']
        forwarded = httpx.Request(request.method, request.url, headers=headers, content=content,
                                  extensions=request.extensions)
        return self.delegate.handle_request(forwarded)

    def close(self):
        # The model wrapper owns the underlying transport lifecycle.
        pass


class CompressionModel:
    def __init__(self, base):
        if not isinstance(base, DeepSeekModel):
            raise TypeError('wire_compression_requires_deepseek_adapter')
        self.base = base

    def generate(self, operation, payload, schema, **kwargs):
        if operation not in ('resolve', 'answer'):
            return self.base.generate(operation, payload, schema, **kwargs)
        owned = self.base._transport is None
        delegate = self.base._transport if not owned else httpx.HTTPTransport(retries=0)
        transport = CompressionTransport(delegate)
        adapter = DeepSeekModel(self.base.settings, api_key=self.base._api_key, transport=transport)
        try:
            result = adapter.generate(operation, payload, schema, **kwargs)
            return Generation(result.value, {**result.metadata, 'm5_compression': transport.audits})
        except Exception as error:
            if hasattr(error, 'metadata'):
                error.metadata['m5_compression'] = transport.audits
            raise
        finally:
            if owned:
                delegate.close()
