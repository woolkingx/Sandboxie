#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."
python3 docs/plan/local/check-ltest-003.py
