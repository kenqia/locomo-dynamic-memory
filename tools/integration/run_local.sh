#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
exec "${LOCOMO_TEST_PYTHON:-/home/kenqia/my_folder/locomo-dynamic-memory/.venv/bin/python}" tools/integration/run_local.py "$@"
