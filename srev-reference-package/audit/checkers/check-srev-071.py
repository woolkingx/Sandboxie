#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-071 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-071-ipc-async-start-handoff.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-071 failed: schema is not draft-07")
if schema.get("id") != "IPC_ASYNC_START_HANDOFF":
    raise SystemExit("SREV-071 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "CreateThread returns a thread handle on success and NULL on failure",
    "payload may be written only after Dll_AllocTemp returns non-null",
    "worker owns hServerEvent and hServerProcess only after CreateThread succeeds",
    "payload must be freed by the current call",
    "fall back to the synchronous wait and cleanup path",
    "synchronous wait path owns closing hServerEvent and hServerProcess",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/ipc_start.c").read_text()
spec = (ROOT / "docs/plan/srev-071-ipc-async-start-handoff.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX BOOLEAN Ipc_StartServer(")
end = src.index("// Ipc_StartServer_Thread", start)
func = src[start:end]

for term in [
    "args = (ULONG_PTR *)Dll_AllocTemp(sizeof(ULONG_PTR) * 4);\n        if (args) {\n            args[0] = (ULONG_PTR)TruePath;",
    "args[3] = (ULONG_PTR)hServerProcess;",
    "hThread = CreateThread(\n                        NULL, 0, Ipc_StartServer_Thread,\n                        (void *)args, CREATE_SUSPENDED, &idThread);",
    "if (hThread) {",
    "CloseHandle(hThread);",
    "} else {\n\n                Dll_Free(args);\n                Async = FALSE;\n            }",
    "} else {\n\n            Async = FALSE;\n        }",
    "if (! Async) {",
    "WaitForMultipleObjects(\n                NumWaitHandles, WaitHandles, FALSE, 30 * 1000);",
    "CloseHandle(hServerEvent);",
    "if (hServerProcess)\n            CloseHandle(hServerProcess);",
]:
    require(func, term, "Ipc_StartServer source")

if func.index("if (args)") > func.index("args[0] = (ULONG_PTR)TruePath;"):
    raise SystemExit("SREV-071 failed: payload gate appears after first slot write")
if func.index("Dll_Free(args);") > func.index("Async = FALSE;", func.index("Dll_Free(args);")):
    raise SystemExit("SREV-071 failed: CreateThread failure sets fallback before freeing payload")
if "if (Async) {" not in func or "if (! Async) {" not in func:
    raise SystemExit("SREV-071 failed: async branch and sync fallback are not both present")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread",
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_information",
    "https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects",
    "srev-071-ipc-async-start-handoff.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-071: IPC Async Start Handoff",
    "IPC_ASYNC_START_HANDOFF",
    "srev-071-ipc-async-start-handoff.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-071 schema/source gate passed")
