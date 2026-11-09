"""Local personal-release commands; never dispatch a model operation."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen
import uuid

from .config import load_settings
from .release_viewer import DEMO, ExportCatalog

ROOT = Path(__file__).resolve().parents[2]


def report(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def doctor(config=None):
    settings = load_settings(config)
    embedding = Path.home() / ".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots" / settings.embedding_revision
    result = {"python": sys.version.split()[0], "python_312": sys.version_info[:2] == (3, 12),
              "dependencies": {name: importlib.metadata.version(name) for name in
                               ("fastapi", "streamlit", "uvicorn", "pydantic", "numpy", "rank-bm25")},
              "embedding_revision": settings.embedding_revision,
              "embedding_cached": embedding.is_dir(),
              "embedding_package_installed": importlib.util.find_spec("sentence_transformers") is not None,
              "database": "absent_will_be_created_on_normal_start",
              "replay": ExportCatalog(DEMO / "manifest.json").verify(),
              "provider": "optional; no credential read and no provider request"}
    if settings.db_path.exists():
        try:
            with sqlite3.connect(settings.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                result["database"] = "ok" if db.execute("PRAGMA quick_check").fetchone()[0] == "ok" else "corrupt"
        except sqlite3.Error:
            result["database"] = "unreadable_or_corrupt"
    report(result)
    return 1 if result["database"] in {"corrupt", "unreadable_or_corrupt"} else 0


def check_ports(ports):
    if len(set(ports)) != len(ports):
        raise ValueError("API and UI ports must differ")
    for port in ports:
        if not 1 <= port <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        try:
            with socket.socket() as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
        except OSError:
            raise ValueError(f"Port {port} is already occupied; choose another port") from None


def stop_processes(processes):
    for process in processes:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    for process in processes:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def serve(args):
    check_ports([args.api_port, args.ui_port])
    run = ROOT / "var/release-runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True, mode=0o700)
    env = dict(os.environ)
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    replay = args.command == "replay-offline-demo"
    if replay:
        # The independent replay factory never creates SQLite or model adapters.
        factory, ui = "locomo_memory.release_viewer:create_replay_app", "replay_ui.py"
        env.pop("LOCOMO_CONFIG", None)
        # Catalog selection is explicit on each run. Do not inherit an unexpected catalog.
        env.pop("LOCOMO_REPLAY_MANIFEST", None)
        env.pop("LOCOMO_REPLAY_DIRECTORY", None)
        if args.manifest:
            env["LOCOMO_REPLAY_MANIFEST"] = str(args.manifest.resolve())
            if args.directory:
                env["LOCOMO_REPLAY_DIRECTORY"] = str(args.directory.resolve())
    else:
        factory, ui = "locomo_memory.api:create_app", "console_ui.py"
        settings = load_settings(args.config)
        config = settings.snapshot()
        config["db_path"] = str(settings.db_path.resolve()) if args.config or "LOCOMO_CONFIG" in os.environ else str(ROOT / "var/personal-app/memory.sqlite3")
        config["api_url"] = f"http://127.0.0.1:{args.api_port}"
        # Write a fresh launch snapshot; never modify the user's config or database.
        config_path = run / "config.toml"
        config_path.write_text("\n".join(f"{key} = {str(value).lower() if isinstance(value, bool) else json.dumps(value)}" for key, value in config.items() if value is not None) + "\n")
        config_path.chmod(0o600)
        env["LOCOMO_CONFIG"] = str(config_path)
    commands = [
        [sys.executable, "-m", "uvicorn", factory, "--factory", "--host", "127.0.0.1", "--port", str(args.api_port), "--no-access-log"],
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "src/locomo_memory" / ui), "--server.address", "127.0.0.1", "--server.port", str(args.ui_port), "--server.headless", "true", "--browser.gatherUsageStats", "false"],
    ]
    processes, logs = [], []
    old_handlers = {}

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    for sig in (signal.SIGINT, signal.SIGTERM):
        old_handlers[sig] = signal.signal(sig, interrupted)
    try:
        for i, command in enumerate(commands):
            log = (run / f"service-{i}.log").open("x")
            (run / f"service-{i}.log").chmod(0o600)
            logs.append(log)
            processes.append(subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True))
        endpoints = [f"http://127.0.0.1:{args.api_port}/health", f"http://127.0.0.1:{args.ui_port}/_stcore/health"]
        deadline = time.monotonic() + 45
        while True:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError(f"Service startup failed; inspect protected logs at {run}")
            try:
                for endpoint in endpoints:
                    with urlopen(endpoint, timeout=1) as response:
                        if response.status != 200:
                            raise OSError("Health failed")
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Health timeout; inspect protected logs at {run}") from None
                time.sleep(0.2)
        report({"status": "ready", "mode": "Synthetic / Offline Replay" if replay else "normal_app",
                "api": f"http://127.0.0.1:{args.api_port}", "ui": f"http://127.0.0.1:{args.ui_port}",
                "stop": "Ctrl+C or SIGTERM stops both owned process groups; database is preserved", "logs": str(run)})
        sys.stdout.flush()
        while all(p.poll() is None for p in processes):
            time.sleep(0.25)
        return next((p.returncode or 1 for p in processes if p.poll() is not None), 1)
    except KeyboardInterrupt:
        return 0
    finally:
        # Repeated Ctrl+C must not interrupt child reaping or leave a service alive.
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            stop_processes(processes)
        finally:
            for log in logs:
                log.close()
            for sig, old in old_handlers.items():
                signal.signal(sig, old)


def validate_six(manifest, directory):
    catalog = ExportCatalog(manifest, directory)
    if set(catalog.entries) != {f"conv-{i}" for i in (26, 30, 41, 42, 43, 44)}:
        raise ValueError("Exactly the six course Build identities are required")
    return catalog.verify()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--config", type=Path)
    for command in ("start", "replay-offline-demo"):
        s = sub.add_parser(command)
        s.add_argument("--api-port", type=int, default=8000 if command == "start" else 18010)
        s.add_argument("--ui-port", type=int, default=8501 if command == "start" else 18510)
        s.add_argument("--config", type=Path)
        s.add_argument("--manifest", type=Path)
        s.add_argument("--directory", type=Path)
    v = sub.add_parser("validate-six-exports")
    v.add_argument("--manifest", type=Path, default=ROOT / "six-memory-exports-manifest.json")
    v.add_argument("--directory", type=Path, required=True)
    t = sub.add_parser("run-tests")
    t.add_argument("--public", action="store_true", help="exclude explicitly marked controlled-data tests")
    t.add_argument("pytest_args", nargs=argparse.REMAINDER)
    for name in ("verify-public-evidence", "verify-private-archive"):
        p = sub.add_parser(name)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return doctor(args.config)
        if args.command in ("start", "replay-offline-demo"):
            return serve(args)
        if args.command == "validate-six-exports":
            report(validate_six(args.manifest, args.directory))
        elif args.command == "run-tests":
            selection = "not live_model and not local_embedding" + (" and not controlled_data" if args.public else "")
            print("Offline test boundary: " + selection, flush=True)
            extra = args.pytest_args[1:] if args.pytest_args[:1] == ["--"] else args.pytest_args
            return subprocess.call([sys.executable, "-m", "pytest", "-q", "-m", selection, *extra], cwd=ROOT)
        else:
            from .release_evidence import verify_files
            report(verify_files(args.manifest, args.directory, private=args.command == "verify-private-archive"))
        return 0
    except (ValueError, OSError, KeyError, RuntimeError, sqlite3.Error) as error:
        # Do not print validation inputs, raw logs, model responses or credentials.
        safe = str(error) if isinstance(error, RuntimeError) or str(error).startswith("Port ") else type(error).__name__
        print(f"Release check failed: {safe}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
