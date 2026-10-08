#!/usr/bin/env bash
set -euo pipefail
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python check.py
fi
exec python3 check.py
