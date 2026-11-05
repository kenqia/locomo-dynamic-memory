"""Budget a complete ordinary Dynamic request without silently dropping facts."""
from .model import request_token_estimate
from .query_schemas import EffectiveResolution

COMPLETE_INPUT_VERSION = 'complete-dynamic-input-v1-no-omission'


def complete_resolution_input(payload, settings):
    """Return the full validation context and audit; callers reject an overrun.

    Relation-connected packing lost all three cited facts in an old human-
    accepted adoption answer. A budget cannot prove any removed fact irrelevant.
    Ordinary Dynamic therefore keeps the packet intact and fails before HTTP
    when the complete request cannot fit. Existing raw-fallback packing is a
    separate historical policy and remains separately identifiable.
    """
    memories = {memory['memory_id']: memory for memory in payload['memories']}
    sources = {source['source_id']: source for source in payload['sources']}
    count = request_token_estimate('resolve', payload, EffectiveResolution)
    fits = count <= settings.resolution_input_budget
    audit = {
        'input_policy_version': COMPLETE_INPUT_VERSION,
        'input_token_count': count, 'input_budget': settings.resolution_input_budget,
        'within_budget': fits, 'truncated': False, 'omitted_groups': [],
        'complete_memory_ids': list(memories),
        'source_delivery': {'expected_source_ids': list(sources), 'attempted_source_ids': [],
                            'delivered_source_ids': [], 'status': 'not_sent'},
    }
    if not fits:
        audit['error_code'] = 'complete_resolution_input_budget_exceeded'
    return {'memories': memories, 'sources': sources,
            'input_budget': settings.resolution_input_budget}, audit


def record_delivery(delivery, metadata, *, accepted, error_code=None):
    calls = metadata.get('calls', [])
    attempted = accepted or bool(calls)
    received = accepted or any(c.get('response_received') for c in calls)
    ids = delivery['expected_source_ids']
    delivery.update(attempted_source_ids=ids if attempted else [],
                    delivered_source_ids=ids if received else [],
                    status='accepted' if accepted else 'request_attempted' if attempted else 'not_sent',
                    provider_accepted=True if accepted else False if error_code=='context_length_exceeded' else None)
