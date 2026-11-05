#!/bin/sh
# Use the existing dependency environment; do not load config or account launchers.
set -eu
cd "$(dirname "$0")/../.."
PYTHON=${LOCOMO_TEST_PYTHON:-/home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python}
unset DEEPSEEK_API_KEY OPENAI_API_KEY CODEX_ACCESS_TOKEN LOCOMO_LIVE_MODEL LOCOMO_LOCAL_EMBEDDING LOCOMO_CONFIG
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$PWD/tools/integration/offline_guard:$PWD/src:$PWD/tests"
exec "$PYTHON" -m pytest -m 'not live_model and not local_embedding' "$@"
