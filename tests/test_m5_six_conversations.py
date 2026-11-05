"""Import all six conversations using conversation-only SQL snapshots, never holdout QA."""
import json
from pathlib import Path
import pytest

from fastapi.testclient import TestClient

from locomo_memory.api import create_app
from locomo_memory.config import Settings


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.controlled_data
def test_six_conversation_only_import_keeps_every_source_identity(tmp_path):
    raw = ROOT/'var/m5-development/replay-v1/conversation-only'
    if not raw.is_dir():
        pytest.skip('Private M5 conversation-only snapshots not present; run tools.m5.offline first')
    originals = {}
    samples = []
    for conv in ('conv-26','conv-30','conv-41','conv-42','conv-43','conv-44'):
        sources = json.loads((raw/(conv+'.json')).read_text())
        originals[conv] = sources
        speakers = list(dict.fromkeys(s['speaker'] for s in sources))
        assert len(speakers) == 2
        conversation = dict(speaker_a=speakers[0],speaker_b=speakers[1])
        for source in sources:
            session = source['session_id']
            conversation[session+'_date_time'] = source['session_time']
            conversation.setdefault(session,[]).append({k:source[k] for k in ('dia_id','speaker','text')})
        samples.append(dict(sample_id=conv,conversation=conversation))
    app = create_app(Settings(db_path=tmp_path/'six-only.sqlite3'))
    with TestClient(app) as client:
        imported = client.post('/imports',json=dict(data=samples,version='m5-conversation-only',license='LoCoMo upstream; original provenance retained separately'))
        assert imported.status_code == 201
        dataset = imported.json()['dataset_id']
        assert client.get(f'/datasets/{dataset}/conversations').json()['total'] == 6
        for conv, sources in originals.items():
            fetched = []
            for offset in range(0,len(sources),100):
                response = client.get(f'/datasets/{dataset}/conversations/{conv}/turns',params=dict(limit=100,offset=offset))
                assert response.status_code == 200
                fetched += response.json()['items']
            assert len(fetched) == len(sources)
            for expected, actual in zip(sources,fetched):
                assert actual['source_id'] == f'{dataset}/{conv}/{expected["dia_id"]}'
                assert {k:actual[k] for k in ('dia_id','speaker','text','session_id','session_time','position')} == {
                    k:expected[k] for k in ('dia_id','speaker','text','session_id','session_time','position')}
