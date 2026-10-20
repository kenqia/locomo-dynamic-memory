import json

import pytest
from pydantic import ValidationError

from locomo_memory.config import Settings


@pytest.mark.parametrize('field', [
    'extraction_thinking_effort', 'relation_thinking_effort', 'query_analysis_thinking_effort',
    'resolution_thinking_effort', 'answer_thinking_effort',
])
def test_stage_effort_is_validated_and_saved(field):
    assert Settings(**{field: 'low'}).snapshot()[field] == 'low'
    with pytest.raises(ValidationError):
        Settings(**{field: 'unsupported'})


@pytest.mark.parametrize("api_url", [
    "http://synthetic-user:synthetic-rejected-secret@127.0.0.1:8000",
    "http://synthetic-rejected-secret@127.0.0.1:8000",
    "http://127.0.0.1:8000?api_key=synthetic-rejected-secret",
])
def test_settings_reject_credential_urls_without_echoing_rejected_input(api_url):
    with pytest.raises(ValidationError) as error:
        Settings(api_url=api_url)
    assert "synthetic-rejected-secret" not in str(error.value)
    assert "synthetic-rejected-secret" not in error.value.json()
    assert "synthetic-rejected-secret" not in json.dumps(error.value.errors(), default=str)
    assert error.value.errors()[0]["loc"] == ("api_url",)
