"""Trim query transport overhead after the controller has pinned evidence scope."""

QUERY_PAYLOAD_VERSION = 'query-semantic-fields-v2'
QUERY_PAYLOAD_GUIDANCE = (
    "In input evidence, omitted optional time or applicability fields and omitted "
    "support_quote/update_evidence mean unknown or no supplied support. They never "
    "prove timeless validity, a satisfied condition, or an event connection. "
    "Explicit false conditions and supplied evidence remain authoritative."
)


def without_unknowns(value, fields):
    return {k: v for k, v in value.items() if k not in fields or v is not None}


def query_wire_payload(operation, payload):
    """Keep every claim, source, time and reference; omit only known admin fields.

    Full objects remain in the controller and Trace for endpoint scope validation.
    Unknown fields survive so future semantic additions cannot silently disappear.
    """
    if operation not in {'resolve', 'resolve_raw', 'answer', 'answer_raw'}:
        return payload
    wire = dict(payload)
    for field, excluded in (
        ('memories', {'build_id', 'dataset_id', 'sample_id'}),
        ('sources', {'dataset_id', 'sample_id'}),
        ('raw_sources', {'dataset_id', 'sample_id'}),
        ('relations', {'build_id'}),
    ):
        if field in wire:
            wire[field] = [{k: v for k, v in item.items() if k not in excluded}
                           for item in wire[field]]
    if isinstance(wire.get('analysis'), dict):
        wire['analysis'] = {k: v for k, v in wire['analysis'].items() if k != 'model_metadata'}
    for memory in wire.get('memories', []):
        if isinstance(memory.get('time'), dict):
            memory['time'] = without_unknowns(memory['time'], {
                'original_expression', 'anchor_source_id', 'event_start', 'event_end',
                'valid_from', 'valid_to', 'basis'})
    if 'relations' in wire:
        wire['relations'] = [without_unknowns(relation, {'support_quote', 'update_evidence'})
                             for relation in wire['relations']]
        for relation in wire['relations']:
            if isinstance(relation.get('applicability'), dict):
                relation['applicability'] = without_unknowns(relation['applicability'], {
                    'from_date', 'to_date', 'condition', 'condition_satisfied',
                    'time_anchor_source_id', 'original_time_expression', 'time_basis'})
    return wire
