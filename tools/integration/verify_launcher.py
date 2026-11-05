"""Probe the actual local launch environment with synthetic account placeholders."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from run_local import ROOT, offline_environment

names = ('DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'CODEX_ACCESS_TOKEN', 'LOCOMO_LIVE_MODEL')
with patch.dict(os.environ, {name:'synthetic-never-use' for name in names}):
    env = offline_environment(ROOT, ROOT / 'var/integration-sandbox/config.toml')
assert all(name not in env for name in names)
probe = """
import socket
for action in (lambda:socket.getaddrinfo('example.invalid',443),
               lambda:socket.socket().connect(('192.0.2.1',443))):
    try: action()
    except RuntimeError as error:
        assert str(error).startswith('integration_offline_external_')
    else: raise AssertionError('external_action_not_blocked')
print('dns_and_socket_blocked')
"""
child = subprocess.run([sys.executable, '-c', probe], env=env, capture_output=True, text=True, timeout=10)
assert child.returncode == 0 and child.stdout.strip() == 'dns_and_socket_blocked'
print(json.dumps(dict(actual_launcher_environment=True, inherited_synthetic_credentials_removed=True,
                     child_external_dns_and_socket_blocked=True, new_live_calls=0), indent=2))
