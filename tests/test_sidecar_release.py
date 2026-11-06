"""ARCH-04 two complete synthetic Build fixtures; preserve storage and identity."""
import json
import pytest
from tools.research_v2.sidecar_compatibility import run_compatibility


def test_two_synthetic_builds_keep_identity_storage_and_rollback(tmp_path):
    out=tmp_path/'compat'
    report=run_compatibility(out)
    assert len(report['fixtures'])==2
    assert len({r['build_id'] for r in report['fixtures']})==2
    assert {r['multi_source_memory'] for r in report['fixtures']}=={True,False}
    assert report['all_passed'] and report['temporary_databases_removed']
    assert report['external_provider_calls']==0 and report['real_historical_builds_checked']==0
    for item in report['fixtures']:
        assert all(item['checks'].values())
        assert item['database_sha256_before']==item['database_sha256_after']
        assert item['export_sha256_before']==item['export_sha256_after']
    assert json.loads((out/'compatibility.json').read_text(encoding='utf-8'))==report
    with pytest.raises(ValueError):run_compatibility(out)
