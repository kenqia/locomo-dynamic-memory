from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(db_path=tmp_path / "memory.sqlite3")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings=settings)) as client:
        yield client


@pytest.fixture
def sample():
    return deepcopy([
        {
            "sample_id": "conv-a",
            "conversation": {
                "speaker_a": "Alex", "speaker_b": "Sam",
                "session_1_date_time": "1:00 pm on 1 May, 2023",
                "session_1": [
                    {"dia_id": "D1:1", "speaker": "Alex", "text": "I live in Paris."},
                    {"dia_id": "D1:2", "speaker": "Sam", "text": "I work in London."},
                ],
                "session_2_date_time": "1:00 pm on 2 May, 2023",
                "session_2": [{"dia_id": "D2:1", "speaker": "Alex", "text": "I moved to Rome."}],
            },
            "qa": [{"question": "Where?", "answer": "ANNOTATION ONLY", "evidence": ["D1:1"]}],
            "event_summary": {"Alex": ["ANNOTATION ONLY"]},
            "observation": {"Alex": ["ANNOTATION ONLY"]},
            "session_summary": "ANNOTATION ONLY",
        }
    ])


def import_sample(client, sample, **metadata):
    return client.post("/imports", json={"data": sample, "version": "synthetic-v1", "license": "test-only", **metadata})
