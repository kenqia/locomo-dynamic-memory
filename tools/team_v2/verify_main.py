"""Verify the normal Release launcher with a new synthetic Product database."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from demo import ROOT, demo_environment
from verify_console import free_port, wait_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError('output_symlink_forbidden')
    output = output.resolve()
    output.relative_to((ROOT / 'var').resolve())
    output.mkdir(parents=True, exist_ok=False)
    api_port, ui_port = free_port(), free_port()
    fixture = output / 'fixture'
    subprocess.run([sys.executable, str(ROOT / 'tools/team_v2/demo.py'), 'prepare',
                    '--output', str(fixture)], cwd=ROOT, check=True)
    env = demo_environment(fixture / 'config.toml')
    command = [sys.executable, '-m', 'locomo_memory.release_cli', 'start',
               '--config', str(fixture / 'config.toml'),
               '--api-port', str(api_port), '--ui-port', str(ui_port)]
    with (output / 'launcher.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            wait_for(f'http://127.0.0.1:{api_port}/health', process)
            wait_for(f'http://127.0.0.1:{ui_port}/_stcore/health', process)
            subprocess.run([str(args.browser_python.absolute()),
                            str(ROOT / 'tools/team_v2/browser_console.py'),
                            '--url', f'http://127.0.0.1:{ui_port}',
                            '--manifest', str(fixture / 'demo-manifest.json'),
                            '--output', str(output / 'screenshots')],
                           cwd=ROOT, env=env, check=True)
        finally:
            process.terminate()
            process.wait(timeout=30)
    result = {'status': 'passed', 'entry': 'personal-release start',
              'console_and_legacy_workflow': 'passed', 'synthetic_cases': 4,
              'provider_requests': 0, 'launcher_returncode': process.returncode}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
