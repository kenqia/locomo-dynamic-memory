"""Regression checks for derived numeric denominators; no Gold or model calls."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m5 import level_c_results as results
from tools.m5.offline import sha, write


@pytest.fixture
def numeric_stage(tmp_path, monkeypatch):
    stage = tmp_path/'synthetic-stage'
    stage.mkdir()
    items, rows = [], []
    for conv in results.DEV:
        for index in range(25):
            for arm in results.ARMS:
                identity = dict(question_id=f'{conv}:qa:{index}', sample_id=conv,
                                arm=arm, stratum='ordinary' if index < 20 else 'diagnostic',
                                outcome='succeeded')
                items.append(identity)
                rows.append(dict(identity, category=4,
                    qa=dict(value=.5, rule='official_category_f1')))
    for name in ('generation-freeze.json', 'plan.json', 'inputs.json', 'sample.json',
                 'settings.json', 'build-identities.json', 'user-authorization-receipt.json',
                 'pricing-recheck.json'):
        write(stage/name, {})
    write(stage/'scores.json', dict(generation_freeze_sha256=sha(stage/'generation-freeze.json'), items=rows))
    write(stage/'terminal-audit-v1.json', dict(generation_freeze_sha256=sha(stage/'generation-freeze.json'),
        items=200, integrity=dict(build_source_memory_relation_projection_index_unchanged=True),
        ledger=dict(physical_ledger_requests=0), groups={}, model_identity={}, resources={}))
    monkeypatch.setattr(results, 'frozen_items', lambda path: (dict(scope='synthetic numeric fixture'), items))
    return stage, tmp_path/'output'


def test_duplicate_score_row_cannot_change_group_denominator(numeric_stage):
    stage, output = numeric_stage
    document = json.loads((stage/'scores.json').read_text())
    document['items'].append(deepcopy(document['items'][0]))
    (stage/'scores.json').write_text(json.dumps(document))
    with pytest.raises(ValueError, match='results_denominator_mismatch'):
        results.run(stage, output)
    assert not output.exists()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -0.1, 1.1, True])
def test_invalid_numeric_score_cannot_be_published(numeric_stage, value):
    stage, output = numeric_stage
    document = json.loads((stage/'scores.json').read_text())
    document['items'][0]['qa']['value'] = value
    (stage/'scores.json').write_text(json.dumps(document))
    with pytest.raises(ValueError, match='results_invalid_score'):
        results.run(stage, output)
    assert not output.exists()


def test_numeric_results_preserve_fixed_group_counts(numeric_stage):
    stage, output = numeric_stage
    result = results.run(stage, output)
    assert result['ordinary']['groups']['dynamic']['planned'] == 80
    assert result['diagnostic']['groups']['hybrid_no_resolution']['planned'] == 20
    published = json.loads((output/'metrics-summary.json').read_text())
    assert published['strata']['ordinary']['comparisons']['all_scorable']['denominator'] == 80
    assert len(json.loads((output/'per-question-metrics.json').read_text())) == 200
