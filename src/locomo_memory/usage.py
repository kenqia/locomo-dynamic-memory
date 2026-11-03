"""Account for reported provider fields without inventing missing usage."""

TOKEN_FIELDS = ('prompt_tokens', 'completion_tokens', 'total_tokens')


def provider_usage(calls, unknown_attempts=0):
    fields = {}
    for field in TOKEN_FIELDS:
        reported = [call['usage'][field] for call in calls if field in call.get('usage', {})]
        fields[field] = {'reported': sum(reported) if reported else None if calls or unknown_attempts else 0,
            'calls_with_reported_usage': len(reported), 'calls_missing_usage': len(calls) - len(reported),
            'complete': len(reported) == len(calls) and unknown_attempts == 0}
    return {'generation_calls': len(calls), 'unknown_attempts': unknown_attempts,
        'calls_without_reported_usage': sum(not call.get('usage') for call in calls),
        'calls_with_partial_usage': sum(bool(call.get('usage')) and any(field not in call['usage'] for field in TOKEN_FIELDS) for call in calls),
        'reported_tokens': {field: fields[field]['reported'] for field in TOKEN_FIELDS}, 'usage_fields': fields,
        'provider_usage_complete': all(field['complete'] for field in fields.values()),
        'provider_retries': sum(call.get('attempt', 1) > 1 for call in calls),
        'reported_provider_seconds': sum(call.get('elapsed_seconds', 0) for call in calls)}
