#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."
python3 docs/plan/check-srev-169.py
