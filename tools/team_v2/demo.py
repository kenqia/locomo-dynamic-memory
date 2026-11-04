"""Start an isolated synthetic offline demo; never use a research database."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/integration'), str(ROOT / 'tests'), str(ROOT / 'tests/browser')]
from run_local import offline_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['prepare', 'api', 'ui'])
    parser.add_argument('--output', type=Path, default=ROOT / 'var/team-v2-demo')
    parser.add_argument('--api-port', type=int, default=18000)
    parser.add_argument('--ui-port', type=int, default=18501)
    args = parser.parse_args()
    requested = args.output.absolute()
    # Only newly owned storage under this clone's ignored var directory is allowed.
    if any(p.is_symlink() for p in [requested, *requested.parents]):
        raise ValueError('demo_output_symlink_forbidden')
    output = requested.resolve()
    output.relative_to((ROOT / 'var').resolve())
    if args.component == 'prepare':
        output.mkdir(parents=True, exist_ok=False)
        config = output / 'config.toml'
        config.write_text('db_path = ' + json.dumps(str(output / 'memory.sqlite3')) + '\n'
                          f'api_url = "http://127.0.0.1:{args.api_port}"\nmodel_retries = 0\ninitial_k = 1\n')
        env = offline_environment(ROOT, config)
        env['PYTHONPATH'] += os.pathsep + str(ROOT / 'tests') + os.pathsep + str(ROOT / 'tests/browser')
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '_seed', str(output)], env=env, cwd=ROOT, check=True)
    else:
        config = output / 'config.toml'
        if not (output / 'demo-manifest.json').is_file() or not config.is_file() or config.is_symlink():
            raise ValueError('run_prepare_first_in_new_owned_output')
        env = offline_environment(ROOT, config)
        env['PYTHONPATH'] += os.pathsep + str(ROOT / 'tests') + os.pathsep + str(ROOT / 'tests/browser')
        if args.component == 'api':
            command = [sys.executable, '-m', 'uvicorn', 'server:app_factory', '--factory', '--host', '127.0.0.1', '--port', str(args.api_port)]
        else:
            command = [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'tools/team_v2/demo_ui.py'), '--server.address', '127.0.0.1', '--server.port', str(args.ui_port), '--server.headless', 'true', '--browser.gatherUsageStats', 'false']
        print('OFFLINE SYNTHETIC DEMO — controlled model adapter, zero provider calls; not QA quality evidence.', flush=True)
        os.chdir(ROOT)
        if os.name == 'nt':
            # Windows exec starts another PID; keep the terminal attached until exit.
            raise SystemExit(subprocess.call(command, env=env))
        os.execve(sys.executable, command, env)


def seed(output):
    import httpx
    from fastapi.testclient import TestClient
    from locomo_memory.api import create_app
    from locomo_memory.config import load_settings
    from locomo_memory.model import DeepSeekModel
    import server
    server._failed_first_extraction = True
    settings = load_settings()
    output = output.resolve()
    output.relative_to((ROOT / 'var').resolve())
    if settings.db_path.resolve() != output / 'memory.sqlite3' or settings.db_path.exists():
        raise ValueError('seed_requires_new_owned_demo_database')
    model = DeepSeekModel(settings, api_key='synthetic-offline-only', transport=httpx.MockTransport(server.provider))
    sample = json.loads((ROOT / 'tests/browser/sample.json').read_text())
    with TestClient(create_app(settings, model=model, embedder=server.BrowserEmbedder())) as client:
        response = client.post('/imports', json={'data': sample, 'version': 'OFFLINE-SYNTHETIC-v2-kickoff', 'license': 'synthetic-test-fixture'})
        assert response.status_code == 201, response.status_code
        dataset_id = response.json()['dataset_id']
        response = client.post('/builds', json={'dataset_id': dataset_id, 'sample_id': 'conv-a'})
        assert response.status_code == 202, response.status_code
        build_id = response.json()['build_id']
        for endpoint, expected in [('index', 201), ('relations', 202), ('publish', 200)]:
            response = client.post(f'/builds/{build_id}/{endpoint}')
            assert response.status_code == expected, (endpoint, response.status_code)
        cases = []
        for question, extra, expected in [
            ('Where does Alex live?', {}, 'sufficient'),
            ('Where did Alex live?', {'requested_date': '2023-05-01'}, 'sufficient'),
            ("What is Sam's birth year?", {}, 'conflict'),
            ("What is Alex's passport number?", {}, 'insufficient'),
        ]:
            response = client.post('/queries', json={'dataset_id': dataset_id, 'sample_id': 'conv-a', 'build_id': build_id, 'question': question, **extra})
            assert response.status_code == 201, response.status_code
            assert response.json()['answer']['status'] == expected
            cases.append({'question': question, 'expected': expected,
                          'status': response.json()['answer']['status'], 'trace_id': response.json()['trace_id']})
    manifest = {'mode': 'OFFLINE_SYNTHETIC', 'dataset_id': dataset_id, 'build_id': build_id,
                'cases': cases, 'provider_calls': 0, 'quality_claim': 'none; deterministic application fixture only'}
    (output / 'demo-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '_seed':
        seed(Path(sys.argv[2]))
    else:
        main()
