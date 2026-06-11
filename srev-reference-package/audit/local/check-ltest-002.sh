#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../.."
python3 docs/plan/local/check-ltest-002.py
