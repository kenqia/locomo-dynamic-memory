"""An operation can lower the configured ceiling, never increase it."""
import httpx
import pytest
from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel, ModelFailure
from locomo_memory.source_reader import SupportedAnswer


@pytest.mark.parametrize('retries,limit,expected', [(0, 10, 1), (2, 1, 1), (2, 2, 2), (1, 10, 2)])
def test_explicit_ceiling_bounds_every_failed_http(retries, limit, expected):
    calls = []
    def response(request):
        calls.append(request)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}],
                                        'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5}})
    model = DeepSeekModel(Settings(model_retries=retries), api_key='synthetic', transport=httpx.MockTransport(response))
    with pytest.raises(ModelFailure) as error:
        model.generate('source_statements', {}, SupportedAnswer, context={'max_attempts': limit})
    assert len(calls) == len(error.value.metadata['calls']) == expected
    assert sum(c['usage']['total_tokens'] for c in error.value.metadata['calls']) == 5 * expected


@pytest.mark.parametrize('limit', [0, -1, True, '1', 1.5, None])
def test_invalid_ceiling_never_starts_a_request(limit):
    def forbidden(request):
        raise AssertionError('No HTTP expected')
    model = DeepSeekModel(Settings(), api_key='synthetic', transport=httpx.MockTransport(forbidden))
    with pytest.raises(ModelFailure, match='invalid_attempt_limit') as error:
        model.generate('source_statements', {}, SupportedAnswer, context={'max_attempts': limit})
    assert error.value.metadata['calls'] == []
