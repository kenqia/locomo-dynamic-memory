"""Credential launcher checks use synthetic files and never call a provider."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


LAUNCHER = Path(__file__).resolve().parents[1] / 'scripts/with_deepseek_env.py'


def run_launcher(tmp_path, *arguments, key=None):
    environment = {**os.environ, 'HOME': str(tmp_path)}
    environment.pop('DEEPSEEK_API_KEY', None)
    if key is not None:
        environment['DEEPSEEK_API_KEY'] = key
    return subprocess.run([sys.executable, str(LAUNCHER), *arguments], env=environment,
                          capture_output=True, text=True, timeout=10)


def credential_file(tmp_path, text):
    path = tmp_path / '.config/locomo-dynamic-memory/deepseek.env'
    path.parent.mkdir(parents=True, mode=0o700)
    path.write_text(text)
    path.chmod(0o600)


def test_existing_environment_takes_precedence_over_invalid_file(tmp_path):
    credential_file(tmp_path, "DEEPSEEK_API_KEY='unterminated-synthetic")
    result = run_launcher(tmp_path, '--', sys.executable, '-c',
                          "import os; assert os.environ['DEEPSEEK_API_KEY']=='synthetic-inherited'; print('ready')",
                          key='synthetic-inherited')
    assert result.returncode == 0 and result.stdout == 'ready\n' and not result.stderr


@pytest.mark.parametrize('assignment', ['DEEPSEEK_API_KEY=synthetic-file',
                                        "export DEEPSEEK_API_KEY='synthetic-file' # comment"])
def test_file_key_reaches_child_without_logging_the_value(tmp_path, assignment):
    credential_file(tmp_path, assignment)
    result = run_launcher(tmp_path, '--', sys.executable, '-c',
                          "import os; assert os.environ['DEEPSEEK_API_KEY']=='synthetic-file'; print('ready')")
    assert result.returncode == 0 and result.stdout == 'ready\n' and not result.stderr


@pytest.mark.parametrize('text', ["DEEPSEEK_API_KEY='synthetic-private-unterminated",
                                 'OTHER_NAME=synthetic-private',
                                 'DEEPSEEK_API_KEY=synthetic-private\x00',
                                 'DEEPSEEK_API_KEY=synthetic-one\nDEEPSEEK_API_KEY=synthetic-two'])
def test_invalid_file_does_not_start_child_or_expose_input(tmp_path, text):
    credential_file(tmp_path, text)
    result = run_launcher(tmp_path, '--', sys.executable, '-c', "print('child-started')")
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == 'credential_file_invalid\n'


def test_missing_source_stops_without_starting_child(tmp_path):
    result = run_launcher(tmp_path, '--', sys.executable, '-c', "print('child-started')")
    assert result.returncode == 2 and not result.stdout
    assert result.stderr == 'credential_source_unavailable\n'


def test_check_reports_presence_without_parsing_or_exposing_file(tmp_path):
    credential_file(tmp_path, "DEEPSEEK_API_KEY='synthetic-private-unterminated")
    result = run_launcher(tmp_path, '--check')
    assert result.returncode == 0 and not result.stderr
    report = json.loads(result.stdout)
    assert not report['environment_present'] and report['credential_file_present']
    assert 'synthetic-private' not in result.stdout


def test_file_content_is_data_and_never_shell_code(tmp_path):
    marker = tmp_path / 'must-not-exist'
    credential_file(tmp_path, f'DEEPSEEK_API_KEY="synthetic-$(touch {marker})"')
    result = run_launcher(tmp_path, '--', sys.executable, '-c',
                          "import os; assert os.environ['DEEPSEEK_API_KEY'].startswith('synthetic-$(touch '); print('ready')")
    assert result.returncode == 0 and result.stdout == 'ready\n' and not marker.exists()
