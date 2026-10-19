#!/usr/bin/env bash
# Run from repository root with an isolated interpreter containing Playwright.
set -euo pipefail
browser_python=${1:?Pass the isolated Playwright Python executable}
# Resolve the directory, retaining the venv's Python symlink and pyvenv.cfg.
browser_python="$(cd "$(dirname "$browser_python")" && pwd)/$(basename "$browser_python")"
smoke_dir=$(mktemp -d /tmp/locomo-browser-smoke.XXXXXX)
# Every run owns its application environment; never synchronize the root .venv.
export UV_PROJECT_ENVIRONMENT="$smoke_dir/app-venv"
app_python="$UV_PROJECT_ENVIRONMENT/bin/python"
api_pid=
ui_pid=
cleanup() {
    result=$?
    trap - EXIT
    for pid in "$api_pid" "$ui_pid"; do
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    printf 'Smoke exit: %s\nSmoke artifacts and logs: %s\n' "$result" "$smoke_dir"
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -p "$smoke_dir/artifacts"
printf 'Smoke artifacts and logs: %s\n' "$smoke_dir"
cat > "$smoke_dir/config.toml" <<EOF
db_path = "$smoke_dir/memory.sqlite3"
api_url = "http://127.0.0.1:18000"
model_retries = 0
initial_k = 1
EOF
export LOCOMO_CONFIG="$smoke_dir/config.toml"
uv sync --locked
"$app_python" - <<'PYTHON'
import socket
for port in (18000, 18501):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
PYTHON
PYTHONPATH=tests:tests/browser "$app_python" -m uvicorn server:app_factory --factory --host 127.0.0.1 --port 18000 --no-access-log > "$smoke_dir/api.log" 2>&1 &
api_pid=$!
"$app_python" -m streamlit run src/locomo_memory/ui.py --server.address 127.0.0.1 --server.port 18501 --browser.gatherUsageStats false --server.headless true > "$smoke_dir/ui.log" 2>&1 &
ui_pid=$!
for attempt in {1..60}; do
    kill -0 "$api_pid" "$ui_pid" 2>/dev/null || { printf 'Service exited; inspect %s\n' "$smoke_dir" >&2; exit 1; }
    if curl --fail --silent http://127.0.0.1:18000/health >/dev/null && curl --fail --silent http://127.0.0.1:18501/_stcore/health >/dev/null; then
        "$browser_python" tests/browser/smoke.py --output "$smoke_dir/artifacts" --app-python "$app_python"
        exit 0
    fi
    sleep 1
done
printf 'Services did not start; inspect %s\n' "$smoke_dir" >&2
exit 1
