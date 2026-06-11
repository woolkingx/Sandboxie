#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
lsa="$root/Sandboxie/core/drv/ipc_lsa.c"
spec="$root/docs/plan/kpath-004-lsad-spec.md"

for op in 0x10 0x1C 0x1D 0x1E 0x22 0x2A 0x2B 0x88 0x89 0x8A 0x8B 0x8C 0x8D; do
    rg -q "case ${op}:" "$lsa"
done

for op in 0x10 0x1C 0x1D 0x1E 0x22 0x88 0x89 0x8A 0x8B 0x8C 0x8D; do
    if rg -q "//case ${op}:" "$lsa"; then
        echo "KPATH-004 check failed: ${op} remains commented out" >&2
        exit 1
    fi
done

rg -q "LsarOpenPolicy" "$spec"
rg -q "DesiredAccess" "$spec"
rg -q "deny known secret/private-data opnums early" "$spec"

echo "KPATH-004 check passed"
