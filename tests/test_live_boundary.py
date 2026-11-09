"""Bounded diagnostics fail closed before an unplanned or repeated provider send."""
import json

import httpx

from locomo_memory.config import Settings
from locomo_memory.model import DeepSeekModel
from test_queries import complete_build, query_provider
from test_retrieval import ControlledEmbedder
from locomo_memory.api import create_app
from fastapi.testclient import TestClient


def test_fixed_retrieval_query_replay_uses_public_pipeline_without_extra_analysis(settings, sample, tmp_path):
    from tools.m5.live_boundary_worker import replay_query

    source_model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(query_provider))
    with TestClient(create_app(settings, model=source_model, embedder=ControlledEmbedder())) as client:
        dataset, bid = complete_build(client, sample)
        trace = client.post('/queries', json={'dataset_id': dataset, 'sample_id':'conv-a',
            'build_id':bid, 'strategy':'dynamic', 'question':'Where did Alex live during April 2023?'}).json()
        source_ids = {sid for c in trace['expanded']['candidates'] for sid in c['memory']['source_ids']}
        sources = client.get(f'/datasets/{dataset}/conversations/conv-a/turns').json()['items']
        # Read the public citation endpoint response rather than private storage.
        assert all('source_id' in source for source in sources)
    observed = []
    def provider(request):
        payload = json.loads(json.loads(request.content)['messages'][1]['content'])
        observed.append(payload)
        return query_provider(request)
    model = DeepSeekModel(settings, api_key='synthetic-test-key', transport=httpx.MockTransport(provider))
    packet = dict(question_id='conv-a:qa:0', question=trace['question'], sample_id='conv-a',
        dataset_id=dataset, build_id=bid, initial=trace['initial'], expanded=trace['expanded'],
        relations=trace['relations'], config=settings.snapshot(), sources=sources)
    result = replay_query(packet, settings, model, tmp_path/'replay.sqlite3')
    assert result['outcome']=='succeeded'
    assert [p['operation'] for p in observed]==['resolve','answer']
    assert result['time']['query_interval']['start']=='2023-04-01'
    assert {s['source_id'] for s in observed[0]['sources']}==source_ids


def stopped_run(tmp_path):
    """A diagnostic state after a terminal stop, with no remaining generation work."""
    from tools.m5.live_boundary import POLICY, ROOT, runner_hashes, sha, write
    (tmp_path/'jobs').mkdir(); (tmp_path/'results').mkdir()
    write(tmp_path/'plan.json',dict(policy=POLICY,runner_hashes=runner_hashes(),snapshots={},
        jobs={},order=[],public_source_sha256=sha(ROOT/'data/raw/locomo/locomo10.json')))
    write(tmp_path/'authorization.json',dict(approved=True,policy=POLICY,
        plan_sha256=sha(tmp_path/'plan.json'),source='Explicit user answer in current chat on 2026-11-09'))
    write(tmp_path/'generation-freeze.json',dict(plan_sha256=sha(tmp_path/'plan.json'),results={}))
    write(tmp_path/'global-stop.json',dict(reason='balance_auth_or_budget_stop'))
    return tmp_path


def test_terminal_generation_stop_prevents_paid_review_processes(tmp_path, monkeypatch):
    from tools.m5.live_boundary import review
    def forbidden(*args,**kwargs):
        raise AssertionError('A terminal generation stop must prevent review sends')
    monkeypatch.setattr('subprocess.run',forbidden)
    private=stopped_run(tmp_path)
    review(private)
    results=[json.loads(p.read_text()) for p in (private/'results').glob('r*.json')]
    assert len(results)==4
    assert all(r['outcome']=='not_executed' for r in results)


def test_changed_blinded_review_packet_blocks_scoring_before_gold(tmp_path):
    import pytest
    from tools.m5.live_boundary import review,score
    private=stopped_run(tmp_path)
    review(private)
    (private/'review-packets.json').write_text('[{"tampered":true}]')
    with pytest.raises(ValueError,match='review_not_frozen_or_changed'):
        score(private,tmp_path/'public')
    assert not (tmp_path/'public').exists()
