"""Own only a Streamlit Replay process; no API or database is started."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from demo import ROOT, demo_environment, server_command
from verify_console import free_port, wait_for


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', help='Export a tracked revision under the owned output for before/after screenshots.')
    parser.add_argument('--browser-script', choices=['browser_replay.py', 'browser_product_final.py', 'browser_console_responsive.py'], default='browser_replay.py')
    args = parser.parse_args()
    requested = args.output.absolute()
    if any(path.is_symlink() for path in (requested, *requested.parents)):
        raise ValueError('output_symlink_forbidden')
    output = requested.resolve()
    output.relative_to((ROOT / 'var').resolve())
    output.mkdir(parents=True, exist_ok=False)
    port = free_port()
    env = demo_environment(ROOT / 'config.example.toml')
    env.pop('LOCOMO_CONFIG', None)
    env['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'var/pw-browsers')
    command = server_command('replay', 0, port)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if args.baseline:
        revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.baseline + '^{commit}'],
                                           cwd=ROOT, text=True).strip()
        archive = output / 'baseline.zip'
        subprocess.run(['git', 'archive', '--format=zip', f'--output={archive}', revision, 'src',
                        'tools/team_v2/replay_ui.py', 'demo_fixture', 'docs/team-v2/research-evidence.json'],
                       cwd=ROOT, check=True)
        baseline = output / 'baseline'
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(baseline)
        env['PYTHONPATH'] = str(baseline / 'src') + os.pathsep + env['PYTHONPATH']
        command = [str(baseline / 'tools/team_v2/replay_ui.py')
                   if arg == str(ROOT / 'tools/team_v2/replay_ui.py') else arg for arg in command]
    env['CONSOLE_EVIDENCE_COMMIT'] = revision
    with (output / 'ui.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, env=env, cwd=ROOT, stdout=log, stderr=log)
        try:
            wait_for(f'http://127.0.0.1:{port}/_stcore/health', process)
            subprocess.run([str(args.browser_python.resolve(strict=True)), str(ROOT / 'tools/team_v2' / args.browser_script),
                            '--url', f'http://127.0.0.1:{port}', '--output', str(output / 'artifacts')],
                           cwd=ROOT, env=env, check=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
