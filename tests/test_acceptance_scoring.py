"""Do not hide a replacement error/fact behind equal aggregate counts."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/acceptance'))
spec=importlib.util.spec_from_file_location('acceptance_score',ROOT/'tools/acceptance/score.py')
score=importlib.util.module_from_spec(spec);spec.loader.exec_module(score)


def test_equal_fact_counts_still_detect_loss_of_a_different_fact():
    initial=dict(covered_fact_ids=['F1'],severe_error_details=[],wrong_refusal=False)
    revised=dict(covered_fact_ids=['F2'],severe_error_details=[],wrong_refusal=False)
    changes=score.pair_changes(initial,revised)
    assert changes['fact_coverage_delta']==0
    assert changes['lost_fact_ids']==['F1'] and changes['gained_fact_ids']==['F2']


def test_equal_error_counts_still_detect_a_new_serious_error():
    initial=dict(covered_fact_ids=[],severe_error_details=['wrong date'],wrong_refusal=False)
    revised=dict(covered_fact_ids=[],severe_error_details=['wrong actor'],wrong_refusal=False)
    assert score.pair_changes(initial,revised)['new_severe']==1


def test_missing_task_keeps_initial_checkpoint_and_unattempted_stage(tmp_path,monkeypatch):
    monkeypatch.setattr(score,'OUT',tmp_path)
    (tmp_path/'execution').mkdir()
    data=dict(initial={'answer':'Preserved'},initial_outcome='technical_pass')
    (tmp_path/'execution/task-000-initial-checkpoint.json').write_text(json.dumps({'result':data}))
    assert score.preserved_result('task-000')==data
    assert score.preserved_result('task-001')=={}
