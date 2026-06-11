#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-198 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-198 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-198-scm-notify-apc-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-198 failed: schema is not draft-07")
if schema.get("id") != "SCM_NOTIFY_APC_CONTRACT":
    raise SystemExit("SREV-198 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/scm_notify.c":
    raise SystemExit("SREV-198 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "pNotifyBuffer is checked before SERVICE_NOTIFY dereference",
    "pfnNotifyCallback is non-null before registration succeeds",
    "CreateEvent failure returns the Win32 failure code",
    "CreateThread failure returns the Win32 failure code",
    "Existing notification entries update data and mask on re-registration",
    "QueueUserAPC success gates inactive transition",
    "Scm_WaitServiceState copies current_state before freeing SERVICE_QUERY_RPL",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/dll/scm_notify.c").read_text()
spec = (ROOT / "docs/plan/srev-198-scm-notify-apc-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-198.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

registration = between(
    src,
    "_FX DWORD Scm_NotifyServiceStatusChangeW(",
    "//---------------------------------------------------------------------------\n// Scm_NotifyServiceStatusChangeA",
)
for term in [
    "SERVICE_NOTIFY *data;",
    "BOOLEAN inserted;",
    "if (! pNotifyBuffer)",
    "data = (SERVICE_NOTIFY *)pNotifyBuffer;",
    "dwVersion = data->dwVersion;",
    "if (! data->pfnNotifyCallback)",
    "if (! dwNotifyMask)",
    "if (! Scm_Notify_Global)",
    "return ERROR_NOT_ENOUGH_MEMORY;",
    "OpenThread(THREAD_SET_CONTEXT, FALSE, GetCurrentThreadId())",
    "CloseHandle(handle);",
    "notify_elem->data = data;",
    "notify_elem->mask = dwNotifyMask;",
    "notify_elem->active = TRUE;",
    "Scm_Notify_Global->hEvent = CreateEvent(NULL, FALSE, FALSE, NULL);",
    "Scm_Notify_Global->hThread = CreateThread(",
    "List_Remove(&Scm_Notify_Global->list, notify_elem);",
]:
    require(registration, term, "registration gate")

if not registration.index("if (! pNotifyBuffer)") < registration.index("data = (SERVICE_NOTIFY *)pNotifyBuffer;"):
    raise SystemExit("SREV-198 failed: pNotifyBuffer is dereferenced before null gate")
if not registration.index("data = (SERVICE_NOTIFY *)pNotifyBuffer;") < registration.index("dwVersion = data->dwVersion;"):
    raise SystemExit("SREV-198 failed: data alias is not established before version read")
if not registration.index("if (! data->pfnNotifyCallback)") < registration.index("EnterCriticalSection(Scm_Notify_CritSec);"):
    raise SystemExit("SREV-198 failed: callback gate is after registration lock")
if not registration.index("notify_elem->data = data;") < registration.index("SetEvent(Scm_Notify_Global->hEvent);"):
    raise SystemExit("SREV-198 failed: data is not published before watcher wake")
if not registration.index("notify_elem->mask = dwNotifyMask;") < registration.index("SetEvent(Scm_Notify_Global->hEvent);"):
    raise SystemExit("SREV-198 failed: mask is not published before watcher wake")

thread_proc2 = between(
    src,
    "_FX void Scm_Notify_ThreadProc2(",
    "//---------------------------------------------------------------------------\n// Scm_Notify_ApcProc",
)
for term in [
    "if (data && data->pfnNotifyCallback)",
    "if (QueueUserAPC(Scm_Notify_ApcProc,",
    "notify_elem->state = state;",
    "notify_elem->active = FALSE;",
]:
    require(thread_proc2, term, "APC queue gate")
if not thread_proc2.index("if (QueueUserAPC(Scm_Notify_ApcProc,") < thread_proc2.index("notify_elem->active = FALSE;"):
    raise SystemExit("SREV-198 failed: inactive transition is not gated by QueueUserAPC success")

apc_proc = between(
    src,
    "_FX void Scm_Notify_ApcProc(",
    "//---------------------------------------------------------------------------\n// Scm_WaitServiceState",
)
for term in [
    "SERVICE_NOTIFY *notify_data;",
    "notify_data = (SERVICE_NOTIFY *)data;",
    "if (notify_data->pfnNotifyCallback)",
    "notify_data->pfnNotifyCallback((PVOID)data);",
]:
    require(apc_proc, term, "APC callback pointer gate")

wait_state = between(
    src,
    "_FX DWORD Scm_WaitServiceState(",
    "\n}",
)
for term in [
    "DWORD current_state;",
    "current_state = ss->dwCurrentState;",
    "return current_state;",
]:
    require(wait_state, term, "wait-state copied return")
reject(wait_state, "return ss->dwCurrentState;", "freed service-status return")
if not wait_state.index("current_state = ss->dwCurrentState;") < wait_state.index("Dll_Free(rpl);"):
    raise SystemExit("SREV-198 failed: current_state is not copied before Dll_Free")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-198",
    "owner: Sandboxie/core/dll/scm_notify.c",
    "spec: docs/plan/srev-198-scm-notify-apc-contract.md",
    "schema: docs/plan/srev-198-scm-notify-apc-contract.schema.json",
    "checker: docs/plan/check-srev-198.py",
    "patched source-level after official SCM/APC shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-198 source gate passed")
