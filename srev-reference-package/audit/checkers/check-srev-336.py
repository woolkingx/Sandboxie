#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]
DBWIN_NAMES = [
    "DBWinMutex",
    "DBWIN_BUFFER",
    "DBWIN_BUFFER_READY",
    "DBWIN_DATA_READY",
]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-336 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-336 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-336-ipc-dbwin-trace-suppression.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-336 failed: schema is not draft-07")
if schema.get("id") != "IPC_DBWIN_TRACE_SUPPRESSION":
    raise SystemExit("SREV-336 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/ipc.c":
    raise SystemExit("SREV-336 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Windows OutputDebugString owns debugger output emission",
    "Sysinternals DebugView owns tool-level capture",
    "observed local transport objects and not public Windows API schema",
    "default IPC open list governs DBWIN object access policy",
    "suppresses only monitor trace noise by clearing the trace letter",
    "must not alter the already computed IPC access status",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

ipc = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-336-ipc-dbwin-trace-suppression.md").read_text()
srev_146 = (ROOT / "docs/plan/srev-146-debug-format-buffer-termination.md").read_text()
srev_236 = (ROOT / "docs/plan/srev-236-debug-header-topology.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-336.md").read_text()

open_start = ipc.index("static const WCHAR* openpaths[] = {")
open_end = ipc.index("// multimedia", open_start)
open_block = ipc[open_start:open_end]

trace_start = ipc.index("if (proc->ipc_trace & (TRACE_ALLOW | TRACE_DENY))")
trace_end = ipc.index("if (letter) {\n\n            ULONG mon_type", trace_start)
trace_block = ipc[trace_start:trace_end]

for name in DBWIN_NAMES:
    require(open_block, f'L"*\\\\BaseNamedObjects*\\\\{name}"', "default DBWIN open list")
    require(trace_block, f'L"{name}"', "DBWIN trace suppression block")

for term in [
    "if ((! NT_SUCCESS(status)) && (proc->ipc_trace & TRACE_DENY))",
    "else if (NT_SUCCESS(status) && (proc->ipc_trace & TRACE_ALLOW))",
    "SREV-336: suppress DBWIN/DebugView transport objects from IPC",
    "trace noise; the objects remain governed by the default open list.",
    "WCHAR *backslash = wcsrchr(Name->Buffer, L'\\\\');",
    "++backslash;",
    "letter = 0;",
]:
    require(trace_block, term, "trace block")

for stale in [
    "$Workaround$ - 3rd party fix",
    "third-party workaround",
]:
    reject(trace_block, stale, "trace block")

for term in [
    "status = STATUS_ACCESS_DENIED;",
    "proc->ipc_trace",
    "MONITOR_IPC",
    "MONITOR_OPEN",
    "MONITOR_DENY",
]:
    require(ipc, term, "IPC policy and trace adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "OutputDebugStringA",
    "DbgPrint",
    "SbieApi_MonitorPutMsg",
]:
    require(srev_146, term, "SREV-146 adjacency")

for term in [
    "OutputDebugStringW",
    "DbgPrint",
    "debugger-output emission",
]:
    require(srev_236, term, "SREV-236 adjacency")

for term in [
    "### SREV-336: IPC DBWIN Trace Suppression",
    "IPC_DBWIN_TRACE_SUPPRESSION",
    "srev-336-ipc-dbwin-trace-suppression.schema.json",
    "Sandboxie/core/drv/ipc.c",
    "Ipc_CheckGenericObject",
    "DBWIN_BUFFER_READY",
    "TRACE_ALLOW",
    "SREV-146",
    "SREV-236",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-336 source gate passed")
