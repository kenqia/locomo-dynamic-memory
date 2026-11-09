from copy import deepcopy
from datetime import datetime, timedelta, timezone
import time

import pytest
from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings


@pytest.fixture(autouse=True)
def stable_offline_utc(monkeypatch, request):
    """Keep synthetic attempt timestamps ordered when the WSL wall clock steps back.

    Patch only the adapter's test clock; source timestamps, production code and
    explicit live model checks retain their original clock semantics.
    """
    if request.node.get_closest_marker('live_model'):
        return
    from locomo_memory import model

    anchor, started = datetime.now(timezone.utc), time.monotonic()

    class OfflineDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = anchor + timedelta(seconds=time.monotonic() - started)
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)

    monkeypatch.setattr(model, 'datetime', OfflineDateTime)


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
