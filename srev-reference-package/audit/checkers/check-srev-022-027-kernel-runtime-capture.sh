#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 docs/plan/check-srev-022-027-kernel-runtime-capture.py
