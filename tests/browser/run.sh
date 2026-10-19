#!/usr/bin/env bash
# Run from repository root with an isolated interpreter containing Playwright.
set -euo pipefail
browser_python=${1:?Pass the isolated Playwright Python executable}
smoke_dir=$(mktemp -d /tmp/locomo-browser-smoke.XXXXXX)
cat > "$smoke_dir/config.toml" <<EOF
db_path = "$smoke_dir/memory.sqlite3"
api_url = "http://127.0.0.1:18000"
model_retries = 0
initial_k = 1
EOF
export LOCOMO_CONFIG="$smoke_dir/config.toml"
uv sync --locked
.venv/bin/python - <<'PYTHON'
import socket
for port in (18000, 18501):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
PYTHON
PYTHONPATH=tests:tests/browser uv run --locked uvicorn server:app_factory --factory --host 127.0.0.1 --port 18000 --no-access-log > "$smoke_dir/api.log" 2>&1 &
api_pid=$!
uv run --locked streamlit run src/locomo_memory/ui.py --server.address 127.0.0.1 --server.port 18501 --browser.gatherUsageStats false --server.headless true > "$smoke_dir/ui.log" 2>&1 &
ui_pid=$!
cleanup() {
    kill "$api_pid" "$ui_pid" 2>/dev/null || true
    wait "$api_pid" "$ui_pid" 2>/dev/null || true
}
trap cleanup EXIT
for attempt in {1..60}; do
    kill -0 "$api_pid" "$ui_pid" 2>/dev/null || { printf 'Service exited; inspect %s\n' "$smoke_dir" >&2; exit 1; }
    if curl --fail --silent http://127.0.0.1:18000/health >/dev/null && curl --fail --silent http://127.0.0.1:18501/_stcore/health >/dev/null; then
        "$browser_python" tests/browser/smoke.py --output "$smoke_dir/artifacts"
        printf 'Smoke artifacts: %s\n' "$smoke_dir/artifacts"
        exit 0
    fi
    sleep 1
done
printf 'Services did not start; inspect %s\n' "$smoke_dir" >&2
exit 1
