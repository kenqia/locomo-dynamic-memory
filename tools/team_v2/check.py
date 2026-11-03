"""Run the public offline suite without restricted historical artifacts."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
# These modules require the excluded official corpus or historical experiment plans.
# They remain in the snapshot for authorized local use and are not counted as passed.
EXCLUDED_MODULES = ['test_experiment.py', 'test_evaluation_plans.py', 'test_evidence_coverage_experiment.py']
EXCLUDED_TESTS = [
    'test_repeat_report_keeps_failed_item_in_denominator',
    'test_official_data_provenance_and_source_mapping',
    'test_real_pair_artifact_is_complete_unique_and_keeps_unknowns',
    'test_offline_preparation_reuses_the_official_plan_and_refuses_started_runs',
]

if __name__ == '__main__':
    env = {k: v for k, v in os.environ.items() if k not in ('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN', 'LOCOMO_CONFIG')}
    env.update(LOCOMO_LIVE_MODEL='0', LOCOMO_LOCAL_EMBEDDING='0', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in ['tools/integration/offline_guard', 'src', 'tests']))
    cmd = [sys.executable, '-m', 'pytest', '-m', 'not live_model and not local_embedding']
    cmd += ['--ignore=tests/' + p for p in EXCLUDED_MODULES]
    cmd += ['-k', ' and '.join('not ' + p for p in EXCLUDED_TESTS)]
    raise SystemExit(subprocess.call(cmd + (sys.argv[1:] or ['-q', '--tb=short']), cwd=ROOT, env=env))
