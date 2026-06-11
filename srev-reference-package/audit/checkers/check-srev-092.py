#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-092 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-092-scm-msi-loader-unload-event-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-092 failed: schema is not draft-07")
if schema.get("id") != "SCM_MSI_LOADER_UNLOAD_EVENT_OWNER":
    raise SystemExit("SREV-092 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SBIE_WindowsInstallerInUse named event",
    "sub-module init functions are called on load and unload_func is optional",
    "Scm_MsiDll(NULL) unload cleanup",
    "MsiCloseHandle closes a per-thread installer handle",
    "MsiCloseAllHandles is diagnostic",
    "source path now releases the process event hold on msi.dll unload",
    "runtime capture must prove the last-user edge across MSI module lifetime",
    "shared user-mode lifecycle capture records must use feature_path msi-last-user-event",
]:
    require(contracts, term, "schema")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "supported Windows 10 releases",
    "supported Windows 11 releases",
    "install",
    "repair",
    "uninstall",
    "advertised repair",
    "custom action process",
    "one client process",
    "multiple concurrent client processes",
    "nested custom action process",
    "early client crash",
    "msi.dll load notification",
    "msi.dll unload notification",
    "Ldr_MyDllCallbackNew load state",
    "Ldr_MyDllCallbackNew unload state",
    "CreateEvent(SBIE_WindowsInstallerInUse)",
    "MSI server OpenEvent success",
    "MSI server OpenEvent failure",
    "last handle close",
    "MsiOpenPackage",
    "MsiOpenProduct",
    "MsiCloseHandle",
    "MsiCloseAllHandles diagnostic readback",
    "sandboxed MSIServer start",
    "wait-loop polling",
    "non-exit while live installer handle remains",
    "non-exit while custom action remains",
    "another thread still owns an MSI handle",
    "non-MSI process loading and unloading unrelated DLLs",
]:
    require(matrix, term, "schema runtime capture matrix")

scm_msi = (ROOT / "Sandboxie/core/dll/scm_msi.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
scm_create = (ROOT / "Sandboxie/core/dll/scm_create.c").read_text()
spec = (ROOT / "docs/plan/srev-092-scm-msi-loader-unload-event-owner.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "static const WCHAR *_MsiServerInUseEventName = SBIE L\"_WindowsInstallerInUse\";",
    "static HANDLE   Msi_ServerInUseEvent = NULL;",
    "SREV-092: MSI module lifetime owns the in-use event.",
    "msi.dll unload releases that hold through the",
    "Do not bind this event to MsiCloseHandle",
    "if (!module) {",
    "CloseHandle(Msi_ServerInUseEvent);",
    "Msi_ServerInUseEvent = NULL;",
    "if ((!Msi_ServerInUseEvent) && (!Scm_IsMsiServer))",
    "Msi_ServerInUseEvent = CreateEvent(",
]:
    require(scm_msi, term, "scm_msi.c MSI event owner")

for stale in [
    "XXX - Ldr module no longer does unload notifications",
    "so we might rely on MsiCloseHandle instead",
    "Msi_ServerInUseEvent = FALSE",
]:
    if stale in scm_msi:
        raise SystemExit(f"SREV-092 failed: stale MSI unload cleanup shape remains {stale!r}")

for term in [
    "BOOLEAN(*unload_func)(HMODULE);",
    "{ L\"msi.dll\",               Scm_MsiDll,                     0, Scm_MsiDll}",
    "{ L\"msi.dll\",               Scm_MsiDll,",
    "if (LoadState) {",
    "ok = dll->init_func(ImageBase);",
    "else {",
    "if (dll->unload_func) {",
    "ok = dll->unload_func(NULL);",
    "dll->state = 0;",
    "SbieDll_UnHookModule(ImageBase);",
]:
    require(ldr, term, "ldr.c module callback topology")

if "dll->init_func(NULL)" in ldr or "dll->init_func(ImageBase)" not in ldr:
    raise SystemExit("SREV-092 failed: unexpected unload init_func topology")

for term in [
    "if (Scm_IsMsiServer)",
    "Scm_SetupMsiWaiter();",
]:
    require(scm_create, term, "scm_create.c MSI server waiter handoff")

for term in [
    "OpenEvent(",
    "EVENT_MODIFY_STATE",
    "ExitProcess(0);",
    "CloseHandle(Msi_ServerInUseEvent);",
    "Msi_ServerInUseEvent = NULL;",
]:
    require(scm_msi, term, "scm_msi.c waiter/event handle behavior")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-092: SCM MSI Loader Unload Event Owner",
    "SCM_MSI_LOADER_UNLOAD_EVENT_OWNER",
    "Runtime Capture Matrix",
    "Shared Runtime Capture Evidence",
    "srev-092-322-user-lifecycle-runtime-capture-playbook.md",
    "srev-092-322-user-lifecycle-runtime-capture.schema.json",
    "msi-last-user-event",
    "Windows gate: validate captured MSI lifecycle records",
    "custom-action entry paths",
    "concrete runtime capture matrix",
    "srev-092-scm-msi-loader-unload-event-owner.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-092 schema/source gate passed")
