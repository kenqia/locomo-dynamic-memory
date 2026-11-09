"""Run the existing browser acceptance on owned, offline API/UI processes.

Reuse the application's installed interpreter and a separate Playwright venv.
All configuration, databases and browser artifacts are newly created in --output.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/integration'))
from run_local import offline_environment


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def opt_in_smoke():
    """Explicit B03/B05 calls, separately from the production HTTP routes."""
    from locomo_memory.config import Settings
    from locomo_memory.model import DeepSeekModel
    from locomo_memory.source_answer_reader import SourceAnswerReader
    from locomo_memory.revised_source_reader import RevisedSourceReader
    from locomo_memory.selective_context import predecessor_context

    sources = [dict(source_id='synthetic/conv-a/D1:1', text='Alex painted a bridge.',
                    dataset_id='synthetic', sample_id='conv-a', dia_id='D1:1',
                    speaker='Alex', session_id='s1', session_time='1 May 2023', position=0)]
    payload = dict(question='What did Alex paint?', status='sufficient', sources=sources, memories=[])
    context = dict(status='sufficient', memories={}, raw_sources={s['source_id']: s for s in sources},
                   input_budget=12000)
    requests = []

    def provider(request):
        requests.append(json.loads(request.content))
        value = dict(status='sufficient', claims=[dict(text='Alex painted a bridge.', evidence_refs=['E0'])])
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {
            'content': json.dumps(value)}}], 'usage': {'prompt_tokens': 20, 'completion_tokens': 5,
                                                    'total_tokens': 25}})

    model = DeepSeekModel(Settings(model_retries=0), api_key='synthetic-only',
                         transport=httpx.MockTransport(provider))
    initial = SourceAnswerReader(model).generate(payload, context=context)
    revised = RevisedSourceReader(model).generate(payload, context=context)
    delivered, audit = predecessor_context(sources, sources, max_turns=60, token_budget=12000)
    assert initial.answer == revised.final_answer
    assert delivered == sources and not audit['truncated']
    assert len(requests) == 3 and revised.usage['generation_calls'] == 2
    return dict(source_reader='passed', revision='passed', selective_context='passed',
                mock_http_calls=len(requests), real_model_calls=0, default_api_registration=False)


def run(output, browser_python):
    output.mkdir(parents=True, exist_ok=False)
    api_port, ui_port = free_port(), free_port()
    config = output / 'config.toml'
    config.write_text('db_path = ' + json.dumps(str(output / 'memory.sqlite3')) + '\n'
                      f'api_url = "http://127.0.0.1:{api_port}"\nmodel_retries = 0\ninitial_k = 1\n')
    env = offline_environment(ROOT, config)
    env['PYTHONPATH'] += ':' + str(ROOT / 'tests') + ':' + str(ROOT / 'tests/browser')
    commands = {
        'api': [sys.executable, '-m', 'uvicorn', 'server:app_factory', '--factory',
                '--host', '127.0.0.1', '--port', str(api_port), '--no-access-log'],
        'ui': [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'src/locomo_memory/ui.py'),
               '--server.address', '127.0.0.1', '--server.port', str(ui_port),
               '--server.headless', 'true', '--browser.gatherUsageStats', 'false'],
    }
    processes, logs = [], []
    try:
        for name, command in commands.items():
            log = (output / (name + '.log')).open('x')
            logs.append(log)
            processes.append(subprocess.Popen(command, cwd=ROOT, env=env,
                                              stdout=log, stderr=subprocess.STDOUT))
        with httpx.Client(trust_env=False, timeout=2) as client:
            for port, path in [(api_port, '/health'), (ui_port, '/_stcore/health')]:
                deadline = time.monotonic() + 30
                while True:
                    if any(p.poll() is not None for p in processes):
                        raise RuntimeError('owned_service_exited')
                    try:
                        if client.get(f'http://127.0.0.1:{port}{path}').status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError('service_start_timeout')
                    time.sleep(0.1)
        subprocess.run([str(browser_python), str(ROOT / 'tests/browser/smoke.py'),
                        '--api', f'http://127.0.0.1:{api_port}', '--ui', f'http://127.0.0.1:{ui_port}',
                        '--output', str(output / 'artifacts'), '--app-python', sys.executable],
                       cwd=ROOT, env=env, check=True, timeout=240)
        with (output / 'opt-ins.json').open('x') as stream:
            json.dump(opt_in_smoke(), stream, indent=2)
    finally:
        for process in processes:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-python', type=Path, required=True)
    args = parser.parse_args()
    run(args.output.absolute(), args.browser_python.absolute())
