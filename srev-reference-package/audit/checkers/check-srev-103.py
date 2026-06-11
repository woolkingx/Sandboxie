#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-103 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-103-win32k-current-thread-gui-state.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-103 failed: schema is not draft-07")
if schema.get("id") != "WIN32K_CURRENT_THREAD_GUI_STATE":
    raise SystemExit("SREV-103 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "IsGUIThread documents GUI state and optional conversion for the calling thread",
    "Thread Connection to a Desktop assigns a desktop to the thread making the connection",
    "PsGetCurrentThread returns the executive thread object for the current thread",
    "PsConvertToGuiThread and KiConvertToGuiThread are not documented WDK DDIs",
    "current-thread Win32 state guard, not a process-level Win32 state guard",
    "keeps Thread_SetThreadToken, handler dispatch, Sbie_InvokeSyscall_asm",
    "does not implement private GUI-thread conversion",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/syscall_win32.c").read_text()
spec = (ROOT / "docs/plan/srev-103-win32k-current-thread-gui-state.md").read_text()
ledger = read_combined_ledger(ROOT)
my_winnt = (ROOT / "Sandboxie/core/drv/my_winnt.h").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "IsGUIThread",
    "calling thread",
    "desktop to the thread making the connection",
    "PsGetCurrentThread",
    "PsConvertToGuiThread",
    "KiConvertToGuiThread",
    "not documented WDK DDIs",
]:
    require(spec, term, "spec official shape")

for term in [
    "Thread_SetThreadToken(proc)",
    "ProbeForRead(user_args, args_len",
    "handler1_func",
    "Direct win32k invocation bypasses the kernel system-service entry",
    "PsConvertToGuiThread / KiConvertToGuiThread are private entry",
    "current thread to already have Win32 thread state",
    "PsGetThreadWin32Thread(PsGetCurrentThread())",
    "status = Syscall_Invoke32(proc, entry, user_args)",
    "status = STATUS_INVALID_ADDRESS",
    "Thread_ClearThreadToken()",
]:
    require(source, term, "syscall_win32.c source shape")

for stale in [
    "todo: call KiConvertToGuiThread() or PsConvertToGuiThread()",
    "once this is implemented the below check with MmIsAddressValid will be obsolete",
    "PsGetProcessWin32Process(PsGetCurrentProcess())) { // HasWin32kInitialized",
]:
    if stale in source:
        raise SystemExit(f"SREV-103 failed: stale source shape remains {stale!r}")

for term in [
    "NTOS_API(ULONG_PTR) PsGetThreadWin32Thread(PETHREAD Thread);",
    "thread GUI conversion",
    "SetProcessWindowStation",
    "SetThreadDesktop",
]:
    require(my_winnt + gui, term, "local supporting shape")

for term in [
    "### SREV-103: Win32k Current Thread GUI State",
    "WIN32K_CURRENT_THREAD_GUI_STATE",
    "srev-103-win32k-current-thread-gui-state.schema.json",
    "PsGetThreadWin32Thread(PsGetCurrentThread())",
]:
    require(ledger, term, "ledger")

print("SREV-103 schema/source gate passed")
