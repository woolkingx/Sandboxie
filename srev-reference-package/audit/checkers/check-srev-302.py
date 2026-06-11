#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-302 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-302 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-302-ipc-dcomlaunch-server-liveness-wait.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-302 failed: schema is not draft-07")
if schema.get("id") != "IPC_DCOMLAUNCH_SERVER_LIVENESS_WAIT":
    raise SystemExit("SREV-302 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ipc_start.c":
    raise SystemExit("SREV-302 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ipc_StartServer owns the RpcSs to DcomLaunch second-stage wait topology",
    "WaitForMultipleObjects owns the event-or-process wait result when hServerProcess is available",
    "GetExitCodeProcess probes are legal only when hServerProcess is non-null",
    "RpcSs process termination before DcomLaunch event signal must fail the second-stage wait",
    "SREV-010 owns the unrelated UAC helper timeout boundary",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/ipc_start.c").read_text()
spec = (ROOT / "docs/plan/srev-302-ipc-dcomlaunch-server-liveness-wait.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-302.md").read_text()
srev_010 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-010.md").read_text(),
    (ROOT / "docs/plan/srev-010-uac-helper-wait.md").read_text(),
    (ROOT / "docs/plan/srev-010-uac-helper-wait.schema.json").read_text(),
])

start = source.index("_FX BOOLEAN Ipc_StartServer(")
end = source.index("// Ipc_StartServer_Thread", start)
func = source[start:end]

for term in [
    "SREV-302: while waiting for DcomLaunch event",
    "creation, hServerProcess is the RpcSs liveness",
    "edge. If it exits, the event cannot be trusted",
    "to appear later.",
    "if (hServerProcess\n                                && GetExitCodeProcess(hServerProcess, &rc)\n                                && rc != 0 && rc != STILL_ACTIVE) {",
    "HANDLE DcomWaitHandles[2];",
    "DcomWaitHandles[0] = hEvent;",
    "DcomWaitHandles[1] = hServerProcess;",
    "rc = WaitForMultipleObjects(\n                            2, DcomWaitHandles, FALSE, 30 * 1000);",
    "if (rc == WAIT_OBJECT_0)\n                            break;",
    "if (rc == (WAIT_OBJECT_0 + 1)) {",
    "SbieApi_Log(2204, _format, _dcomlaunch, -4);",
    "bRet = FALSE;",
    "rc = WaitForSingleObject(hEvent, 30 * 1000);",
    "SbieApi_Log(2204, _format, _dcomlaunch, -2);",
]:
    require(func, term, "Ipc_StartServer")

for stale in [
    "hServerProcess should stay running. If hServerProcess exits, probably a crash",
    "we have no chance to open the ServiceInitComplete event. Break to loop.",
]:
    reject(func, stale, "source wording")

if func.index("HANDLE DcomWaitHandles[2];") > func.index("rc = WaitForSingleObject(hEvent, 30 * 1000);"):
    raise SystemExit("SREV-302 failed: multiple-object liveness wait must precede single-event fallback")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "IPC_DCOMLAUNCH_SERVER_LIVENESS_WAIT",
    "DcomWaitHandles[0] = hEvent",
    "DcomWaitHandles[1] = hServerProcess",
    "No process launch policy, service selection, event naming",
]:
    require(spec, term, "spec")

for term in [
    "SBIE_UAC_PROMPT_TIMEOUT_MS",
    "Only the dedicated uac_prompt helper wait is bounded; other Sandboxie WaitForSingleObject calls are out of scope",
    "WaitForSingleObject can return WAIT_OBJECT_0, WAIT_TIMEOUT, or WAIT_FAILED",
]:
    require(srev_010, term, "SREV-010 adjacency")

for term in [
    "### SREV-302: IPC DcomLaunch Server Liveness Wait",
    "IPC_DCOMLAUNCH_SERVER_LIVENESS_WAIT",
    "srev-302-ipc-dcomlaunch-server-liveness-wait.schema.json",
    "Sandboxie/core/dll/ipc_start.c",
    "Ipc_StartServer",
    "SREV-010",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-302 source gate passed")
