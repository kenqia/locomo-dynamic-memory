"""Static repair guidance; never include rejected output or exception messages."""
from .diagnostics import DOMAIN_ERRORS

VALIDATION_RETRY_FEEDBACK_VERSION = 'safe-validation-feedback-v2-budget-aware'

EXTRACTION_TIME_FEEDBACK = {
    'extraction_time_anchor_cited':
        "The memory at field_path has time.anchor_source_id absent from its source_ids. ",
    'extraction_time_expression_required':
        "The memory at field_path has original_expression absent from its cited anchor's raw text. ",
}
EXTRACTION_TIME_RECHECK = (
    "Recheck that memory's source_ids and time fields together against the supplied raw sources. "
    "Copy the time expression from the correct cited anchor only when it supports this claim. "
    "Do not invent evidence, change a supported date or clear time fields just to pass validation. "
    "Regenerate the complete batch, preserving all other supported facts."
)


def query_retry_feedback(operation, previous):
    """Known domain errors can guide an already-authorized finite retry."""
    code = previous.get('error_code')
    if previous.get('outcome') != 'invalid_output' or code not in DOMAIN_ERRORS:
        return None
    if operation in {'resolve', 'resolve_raw'}:
        allowed = code.startswith('resolution_') or code in {
            'applicability_time_evidence_required', 'applicability_range_reversed',
            'condition_evidence_required', 'explicit_condition_required',
            'update_stage_evidence_required', 'update_real_stage_required',
            'update_endpoint_stage_required', 'source_time_expression_required',
        }
        instruction = (
            "Regenerate the complete resolution using only supplied candidates and sources. "
            "Keep one decision per candidate and align selected IDs with those decisions. "
            "Recheck supplemental relation endpoints, dates and conditions against their own sources. "
        )
    elif operation in {'answer', 'answer_raw'}:
        allowed = code.startswith('answer_')
        instruction = (
            "Regenerate the complete answer from delivered evidence only. Preserve the supplied "
            "conflict or insufficient status; sufficient may be downgraded when evidence is missing. "
            "Use only citations supported by delivered memories or explicitly allowed raw sources. "
            "A conflict needs both evidence sides. "
        )
    else:
        return None
    if not allowed:
        return None
    return dict(error_code=code, field_path=previous.get('field_path'), instruction=(
        instruction + DOMAIN_ERRORS[code] + ". Do not invent evidence, clear supported dates, "
        "change uncertainty or patch citations merely to pass validation. "
        "Reassess the evidence and return JSON conforming to the existing schema."
    ))
