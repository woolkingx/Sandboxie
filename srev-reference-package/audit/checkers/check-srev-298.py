#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-298 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-298 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-298-handle-propagated-close-handler-param-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-298 failed: schema is not draft-07")
if schema.get("id") != "HANDLE_PROPAGATED_CLOSE_HANDLER_PARAM_GATE":
    raise SystemExit("SREV-298 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/handle.c":
    raise SystemExit("SREV-298 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Handle_RegisterHandler owns admission of Close, Param, and bPropagate metadata",
    "propagated close handlers are legal only when Param is NULL until a duplicate-param owner exists",
    "Handle_SetupDuplicate copies propagated close handlers with NULL Param only",
    "SREV-070 owns HANDLE_HANDLER node lifetime",
    "this SREV does not change current File_NotifyRecover propagation behavior",
]:
    require(contracts, term, "schema")

handle = (ROOT / "Sandboxie/core/dll/handle.c").read_text()
hdr = (ROOT / "Sandboxie/core/dll/handle.h").read_text()
secure = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
recovery = (ROOT / "Sandboxie/core/dll/file_recovery.c").read_text()
spec = (ROOT / "docs/plan/srev-298-handle-propagated-close-handler-param-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-298.md").read_text()
srev_070 = (ROOT / "docs/plan/ledger/srev-070.md").read_text()

register_start = handle.index("_FX BOOLEAN Handle_RegisterHandler(")
register_end = handle.index("// Handle_UnRegisterHandler", register_start)
register_func = handle[register_start:register_end]

setup_start = handle.index("_FX void Handle_SetupDuplicate(")
setup_func = handle[setup_start:]

for term in [
    "BOOL\t\t\tbPropagate; // SREV-298: duplicate propagation is legal only with NULL Param.",
    "BOOLEAN Handle_RegisterHandler(HANDLE FileHandle, P_HandlerFunc CloseHandler, void* Params, BOOL bPropagate);",
]:
    require(handle + hdr, term, "handle boundary")

for term in [
    "if (!FileHandle || FileHandle == (HANDLE)-1)\n        return FALSE;",
    "if (bPropagate && Params)\n        return FALSE;",
    "newNandler->Param = Params;",
    "newNandler->bPropagate = bPropagate;",
    "A matching close handler is already registered for this handle.",
]:
    require(register_func, term, "Handle_RegisterHandler")

if register_func.index("if (bPropagate && Params)") > register_func.index("EnterCriticalSection"):
    raise SystemExit("SREV-298 failed: bPropagate/Param gate appears after state mutation")

for stale in [
    "incompatible with Param, todo: add duplicate handler",
    "CloseHandlers already registered\"); // todo",
]:
    reject(handle, stale, "handle.c todo")

for term in [
    "Handle_SetupDuplicate(SourceHandle, *TargetHandle);",
    "if (TargetProcessHandle == NtCurrentProcess() && TargetHandle)",
]:
    require(secure, term, "secure duplicate caller")

for term in [
    "if (handler->bPropagate) {",
    "Handle_RegisterHandler(NewFileHandle, handler->Close, NULL, TRUE);",
    "break;",
]:
    require(setup_func, term, "Handle_SetupDuplicate")

for term in [
    "Handle_RegisterHandler(FileHandle, File_NotifyRecover, NULL, TRUE);",
    "_FX void File_NotifyRecover(HANDLE FileHandle, void* CloseParams)",
]:
    require(recovery, term, "current propagated caller")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "HANDLE_PROPAGATED_CLOSE_HANDLER_PARAM_GATE",
    "propagated close handlers are legal only when `Param == NULL`",
    "SREV-070 owns close-handler node lifetime",
    "No existing propagated caller changes behavior",
]:
    require(spec, term, "spec")

for term in [
    "HANDLE_CLOSE_HANDLER_LIFETIME",
    "HANDLE_HANDLER` node",
    "node-lifetime exits",
    "duplicate-handle close-handler propagation remains compatible with existing null-param callers",
]:
    require(srev_070, term, "SREV-070 adjacency")

for term in [
    "### SREV-298: Handle Propagated Close Handler Param Gate",
    "HANDLE_PROPAGATED_CLOSE_HANDLER_PARAM_GATE",
    "srev-298-handle-propagated-close-handler-param-gate.schema.json",
    "Sandboxie/core/dll/handle.c",
    "Handle_RegisterHandler",
    "Handle_SetupDuplicate",
    "File_NotifyRecover",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-298 source gate passed")
