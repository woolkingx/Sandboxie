#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
drv="$root/Sandboxie/core/drv"

rg -q "Ipc_GetRpcMsgId" "$drv/ipc.h" "$drv/ipc_port.c"
rg -q "RPC0: Len=.*Msg20" "$drv/ipc_port.c"
rg -q "RPC1: B16-31" "$drv/ipc_port.c"

if rg -n "ptr\\[20\\]" \
    "$drv/ipc_lsa.c" "$drv/ipc_sam.c" "$drv/ipc_spl.c" "$drv/ipc_port.c"; then
    echo "KPATH-006 check failed: endpoint filters still read ptr[20] directly" >&2
    exit 1
fi

for file in "$drv/ipc_lsa.c" "$drv/ipc_sam.c" "$drv/ipc_spl.c" "$drv/ipc_port.c"; do
    rg -q "Ipc_GetRpcMsgId" "$file"
done

echo "KPATH-006 check passed"
