"""Run main's public offline regression suite with an isolated environment."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

if __name__ == '__main__':
    env = {key: value for key, value in os.environ.items()
           if key not in ('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN', 'LOCOMO_CONFIG')}
    env.update(LOCOMO_LIVE_MODEL='0', LOCOMO_LOCAL_EMBEDDING='0', HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', PYTHONUTF8='1',
               PYTHONPATH=os.pathsep.join(str(ROOT / path) for path in
                                        ('tools/integration/offline_guard', 'src', 'tests')))
    command = [sys.executable, '-m', 'locomo_memory.release_cli', 'run-tests', '--public', '--']
    raise SystemExit(subprocess.call(command + (sys.argv[1:] or ['--tb=short']), cwd=ROOT, env=env))
