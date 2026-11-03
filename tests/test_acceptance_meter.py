"""No paid requests: enforce this study's real physical-call safety gate."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

spec=importlib.util.spec_from_file_location('acceptance_meter',Path(__file__).resolve().parents[1]/'tools/acceptance/meter.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def plan(**changes):
    return dict(money_cap_micro_cny=20000000,maximum_http=152,maximum_wall_seconds=7200,deadline_utc=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(),allowed_returned_models=['deepseek-flash'],**changes)


def request(**changes):
    body=dict(model='deepseek-flash',max_tokens=8192,messages=[],thinking={'type':'disabled'},**changes)
    return httpx.Request('POST','https://api.deepseek.com/chat/completions',json=body)


def response(usage=None,model='deepseek-flash'):
    return httpx.Response(200,json=dict(model=model,usage=usage if usage is not None else dict(prompt_tokens=100,completion_tokens=20,total_tokens=120),choices=[dict(finish_reason='stop',message={'content':'{}','reasoning_content':'MUST_NOT_BE_SAVED'})]))


def test_reservation_is_durable_before_send_and_settles_once(tmp_path):
    calls=[]
    def provider(req):
        with sqlite3.connect(tmp_path/'run/ledger.sqlite3') as db:
            assert db.execute('SELECT state,reserved FROM calls').fetchone()==('reserved_before_send',m.RESERVE_MICRO_CNY)
        calls.append(req);return response()
    meter=m.Meter(tmp_path/'run',plan(),delegate=httpx.MockTransport(provider));meter.task='one'
    meter.handle_request(request())
    assert meter.summary()['physical_http']==1
    assert meter.summary()['estimated_upper_micro_cny']==360
    assert meter.summary()['unsettled_calls']==0
    assert 'MUST_NOT_BE_SAVED' not in meter.db.execute('SELECT response_json FROM calls').fetchone()[0]
    with pytest.raises(m.StopStudy,match='reservation_persistence_failed'):meter.handle_request(request())
    assert len(calls)==1
    meter.finish()


@pytest.mark.parametrize('usage',[{},dict(prompt_tokens=100),dict(prompt_tokens=100,completion_tokens=20,total_tokens=119),dict(prompt_tokens=m.INPUT_CAP+1,completion_tokens=0,total_tokens=m.INPUT_CAP+1)])
def test_unknown_or_invalid_usage_retains_full_reserve_and_observation(tmp_path,usage):
    meter=m.Meter(tmp_path/'run',plan(),delegate=httpx.MockTransport(lambda r:response(usage)))
    meter.task='one'
    with pytest.raises(m.StopStudy):meter.handle_request(request())
    assert meter.summary()['unsettled_reserved_micro_cny']==m.RESERVE_MICRO_CNY
    assert meter.db.execute('SELECT state FROM calls').fetchone()[0]=='response_observed'
    assert json.loads(meter.db.execute('SELECT usage_json FROM calls').fetchone()[0])==usage
    with pytest.raises(m.StopStudy,match='already_stopped'):meter.handle_request(request())
    meter.finish()


def test_timeout_stops_without_resend(tmp_path):
    calls=[]
    def provider(r):calls.append(r);raise httpx.ReadTimeout('synthetic timeout')
    meter=m.Meter(tmp_path/'run',plan(),delegate=httpx.MockTransport(provider));meter.task='one'
    with pytest.raises(m.StopStudy,match='unknown'):meter.handle_request(request())
    with pytest.raises(m.StopStudy):meter.handle_request(request())
    assert len(calls)==1 and meter.summary()['unsettled_calls']==1
    meter.finish()


@pytest.mark.parametrize('limit',['money','http','time'])
def test_limits_block_before_any_http(tmp_path,limit):
    config=plan()
    config.update({'money_cap_micro_cny':m.RESERVE_MICRO_CNY-1} if limit=='money' else {'maximum_http':0} if limit=='http' else {'deadline_utc':'2000-01-01T00:00:00+00:00'})
    sent=[];meter=m.Meter(tmp_path/'run',config,delegate=httpx.MockTransport(lambda r:sent.append(r)));meter.task='one'
    with pytest.raises(m.StopStudy):meter.handle_request(request())
    assert sent==[] and meter.summary()['physical_http']==0
    meter.finish()


def test_persistence_failure_never_sends(tmp_path):
    sent=[];meter=m.Meter(tmp_path/'run',plan(),delegate=httpx.MockTransport(lambda r:sent.append(r)));meter.task='one';meter.db.close()
    with pytest.raises(m.StopStudy,match='persistence_failed'):meter.handle_request(request())
    assert sent==[]


def test_model_identity_change_keeps_cost_and_stops(tmp_path):
    meter=m.Meter(tmp_path/'run',plan(),delegate=httpx.MockTransport(lambda r:response(model='unexpected-model')));meter.task='one'
    with pytest.raises(m.StopStudy,match='identity_changed'):meter.handle_request(request())
    assert meter.summary()['estimated_upper_micro_cny']==360
    with pytest.raises(m.StopStudy):meter.handle_request(request())
    meter.finish()


def test_existing_run_cannot_resume_or_overwrite(tmp_path):
    meter=m.Meter(tmp_path/'run',plan());meter.finish()
    with pytest.raises(FileExistsError):m.Meter(tmp_path/'run',plan())
