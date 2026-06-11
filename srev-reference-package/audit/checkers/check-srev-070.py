#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-070 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-070-handle-close-handler-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-070 failed: schema is not draft-07")
if schema.get("id") != "HANDLE_CLOSE_HANDLER_LIFETIME":
    raise SystemExit("SREV-070 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Dll_Alloc returns non-null",
    "pParams is an optional caller-owned output slot",
    "write the stored Param through *pParams",
    "removed by Handle_UnRegisterHandler must be released with Dll_Free",
    "executed by Handle_ExecuteCloseHandler must be released with Dll_Free",
    "owns HANDLE_HANDLER node lifetime",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/handle.c").read_text()
hdr = (ROOT / "Sandboxie/core/dll/handle.h").read_text()
spec = (ROOT / "docs/plan/srev-070-handle-close-handler-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

register_start = src.index("_FX BOOLEAN Handle_RegisterHandler(")
register_end = src.index("// Handle_UnRegisterHandler", register_start)
register_func = src[register_start:register_end]

unregister_start = src.index("_FX VOID Handle_UnRegisterHandler(")
unregister_end = src.index("// Handle_SetupDuplicate", unregister_start)
unregister_func = src[unregister_start:unregister_end]

execute_start = src.index("_FX VOID Handle_ExecuteCloseHandler(")
execute_end = src.index("// Handle_RegisterHandler", execute_start)
execute_func = src[execute_start:execute_end]

require(
    hdr,
    "VOID Handle_UnRegisterHandler(HANDLE FileHandle, P_HandlerFunc CloseHandler, void** pParams);",
    "handle.h boundary",
)

for term in [
    "HANDLE_HANDLER* newNandler = Dll_Alloc(sizeof(HANDLE_HANDLER));\n        if (!newNandler) {\n            LeaveCriticalSection(&Handle_StatusData_CritSec);\n            return FALSE;\n        }",
    "memzero(&newNandler->list_elem, sizeof(LIST_ELEM));",
    "List_Insert_After(&state->CloseHandlers, NULL, newNandler);",
]:
    require(register_func, term, "Handle_RegisterHandler source")

if register_func.index("if (!newNandler)") > register_func.index("memzero(&newNandler->list_elem"):
    raise SystemExit("SREV-070 failed: allocation gate appears after handler initialization")

for term in [
    "if (pParams) *pParams = handler->Param;",
    "List_Remove(&state->CloseHandlers, handler);",
    "Dll_Free(handler);",
]:
    require(unregister_func, term, "Handle_UnRegisterHandler source")

if unregister_func.index("if (pParams) *pParams") > unregister_func.index("List_Remove(&state->CloseHandlers, handler);"):
    raise SystemExit("SREV-070 failed: param output appears after list removal")
if unregister_func.index("List_Remove(&state->CloseHandlers, handler);") > unregister_func.index("Dll_Free(handler);"):
    raise SystemExit("SREV-070 failed: handler free appears before list removal")
if "if (pParams) pParams = handler->Param;" in unregister_func:
    raise SystemExit("SREV-070 failed: stale local pParams assignment remains")

for term in [
    "handler->Close(FileHandle, handler->Param);",
    "List_Remove(&CloseHandlers, handler);",
    "Dll_Free(handler);",
]:
    require(execute_func, term, "Handle_ExecuteCloseHandler source")

for term in [
    "srev-070-handle-close-handler-lifetime.schema.json",
    "Handle_UnRegisterHandler(HANDLE FileHandle, P_HandlerFunc CloseHandler, void** pParams)",
    "Dll_Free(handler)",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-070: Handle Close Handler Lifetime",
    "HANDLE_CLOSE_HANDLER_LIFETIME",
    "srev-070-handle-close-handler-lifetime.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-070 schema/source gate passed")
