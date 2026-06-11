#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-335 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-335 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-335-ipc-com-server-classifier.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-335 failed: schema is not draft-07")
if schema.get("id") != "IPC_COM_SERVER_CLASSIFIER":
    raise SystemExit("SREV-335 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/ipc.c":
    raise SystemExit("SREV-335 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver-side forced COM server classification",
    "forced processes whose image did not come from inside the box",
    "allowlist remains iexplore exe wmplayer exe winamp exe and kmplayer exe",
    "parent process must exist must be outside the sandbox and must run as system account",
    "marks a classified forced COM server process as untouchable",
    "Custom_ComServer and SREV-256 own the brokered COM handoff topology",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

ipc = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
custom = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
comserver9 = (ROOT / "Sandboxie/core/svc/comserver9.c").read_text()
process_server = (ROOT / "Sandboxie/core/svc/ProcessServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-335-ipc-com-server-classifier.md").read_text()
srev_256 = (ROOT / "docs/plan/srev-256-custom-comserver-broker-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-335.md").read_text()

init_start = ipc.index("_FX BOOLEAN Ipc_InitPaths(")
init_end = ipc.index("// Ipc_IsComServer", init_start)
init_block = ipc[init_start:init_end]

classifier_start = ipc.index("_FX BOOLEAN Ipc_IsComServer(PROCESS *proc)")
classifier_end = ipc.index("// Ipc_InitProcess", classifier_start)
classifier_block = ipc[classifier_start:classifier_end]

custom_start = custom.index("_FX void Custom_ComServer(void)")
custom_end = custom.index("WCHAR *cmdline;", custom_start)
custom_block = custom[custom_start:custom_end]

run_start = process_server.index("WCHAR *ProcessServer::RunSandboxedComServer(")
run_end = process_server.index("// RunSandboxedDupAndCloseHandles", run_start)
run_block = process_server[run_start:run_end]

for term in [
    "if (ok && Ipc_IsComServer(proc))",
    "proc->untouchable = TRUE;",
    "Custom_ComServer",
]:
    require(init_block, term, "Ipc_InitPaths block")

for term in [
    "if (! proc->forced_process)",
    "if (proc->image_from_box)",
    "SREV-335: driver-side forced COM server classifier",
    "brokered SbieSvc handoff owned by Custom_ComServer/SREV-256",
    '_wcsicmp(proc->image_name, L"iexplore.exe")',
    '_wcsicmp(proc->image_name, L"wmplayer.exe")',
    '_wcsicmp(proc->image_name, L"winamp.exe")',
    '_wcsicmp(proc->image_name, L"kmplayer.exe")',
    "MyGetParentId(&ParentId);",
    "if (! ParentId)",
    "pproc = Process_Find(ParentId, NULL);",
    "if (pproc)",
    "MyIsProcessRunningAsSystemAccount(ParentId)",
    "return TRUE;",
]:
    require(classifier_block, term, "Ipc_IsComServer block")

reject(classifier_block, "$Workaround$ - 3rd party fix", "Ipc_IsComServer block")

for term in [
    "CoCreateInstance",
    "SbieDll_RunSandboxed",
    "Custom_ComServer",
    "core/svc/comserver9.c",
]:
    require(custom_block, term, "Custom_ComServer adjacency")

for term in [
    "iexplore.exe",
    "wmplayer.exe",
    "winamp.exe",
    "kmplayer.exe",
]:
    require(comserver9, term, "comserver9 image adjacency")

for term in [
    "RunSandboxedComServer",
    "SBIE_FLAG_FORCED_PROCESS",
    "SBIE_FLAG_PROTECTED_PROCESS",
]:
    require(run_block, term, "ProcessServer forced COM server gate")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "brokered SbieSvc handoff",
    "Custom_ComServer",
    "comserver9.c",
    "CoCreateInstance",
]:
    require(srev_256, term, "SREV-256 adjacency")

for term in [
    "### SREV-335: IPC COM Server Classifier",
    "IPC_COM_SERVER_CLASSIFIER",
    "srev-335-ipc-com-server-classifier.schema.json",
    "Sandboxie/core/drv/ipc.c",
    "Ipc_IsComServer",
    "proc->untouchable",
    "Custom_ComServer",
    "SREV-256",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-335 source gate passed")
