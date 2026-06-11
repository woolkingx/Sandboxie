#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-203 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-203 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-203-gui-wnd-hook-register-lock-exit.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-203 failed: schema is not draft-07")
if schema.get("id") != "GUI_WND_HOOK_REGISTER_LOCK_EXIT":
    raise SystemExit("SREV-203 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiServer.h":
    raise SystemExit("SREV-203 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/svc/GuiServer.cpp":
    raise SystemExit("SREV-203 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "Every exit after EnterCriticalSection in WndHookRegisterSlave passes through LeaveCriticalSection",
    "Thread owner mismatch closes the thread handle before the failure edge",
    "A new WND_HOOK entry is inserted only after HeapAlloc succeeds",
]:
    require(contracts, term, "schema contract")

header = (ROOT / "Sandboxie/core/svc/GuiServer.h").read_text()
src = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-203-gui-wnd-hook-register-lock-exit.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-203.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(header, "ULONG WndHookRegisterSlave(SlaveArgs* args);", "header owner declaration")

fn = between(
    src,
    "ULONG GuiServer::WndHookRegisterSlave(SlaveArgs* args)",
    "//---------------------------------------------------------------------------\n// GetProcessPathList",
)
for term in [
    "ULONG status = STATUS_SUCCESS;",
    "EnterCriticalSection(&m_SlavesLock);",
    "status = STATUS_UNSUCCESSFUL;",
    "goto finish;",
    "status = STATUS_ACCESS_DENIED;",
    "status = STATUS_INSUFFICIENT_RESOURCES;",
    "finish:",
    "LeaveCriticalSection(&m_SlavesLock);",
    "if (status != STATUS_SUCCESS)\n        return status;",
    "rpl->status = STATUS_SUCCESS;",
]:
    require(fn, term, "single-exit lock handling")

reject(fn, "if (!hThread) \n            return STATUS_UNSUCCESSFUL;", "direct OpenThread failure return")
reject(fn, "if (ownerPid != args->pid)\n            return STATUS_ACCESS_DENIED;", "direct owner mismatch return")

if not fn.index("CloseHandle(hThread);") < fn.index("if (ownerPid != args->pid)"):
    raise SystemExit("SREV-203 failed: owner mismatch can occur before CloseHandle")
if not fn.index("finish:") < fn.index("LeaveCriticalSection(&m_SlavesLock);"):
    raise SystemExit("SREV-203 failed: finish label is after LeaveCriticalSection")
if not fn.index("LeaveCriticalSection(&m_SlavesLock);") < fn.index("if (status != STATUS_SUCCESS)"):
    raise SystemExit("SREV-203 failed: failure status returned before lock release")
if not fn.index("if (! whk)") < fn.index("whk->pid = args->pid;"):
    raise SystemExit("SREV-203 failed: allocation failure gate is after WND_HOOK write")
if not fn.index("status = STATUS_INSUFFICIENT_RESOURCES;") < fn.index("whk->pid = args->pid;"):
    raise SystemExit("SREV-203 failed: allocation failure status is after WND_HOOK write")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-203",
    "owner: Sandboxie/core/svc/GuiServer.h",
    "implementation: Sandboxie/core/svc/GuiServer.cpp",
    "spec: docs/plan/srev-203-gui-wnd-hook-register-lock-exit.md",
    "schema: docs/plan/srev-203-gui-wnd-hook-register-lock-exit.schema.json",
    "checker: docs/plan/check-srev-203.py",
    "patched source-level after official critical-section/thread-handle shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-203 source gate passed")
