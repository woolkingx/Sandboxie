#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-312 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-312 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-312-ldr-dll-notification-lock-union-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-312 failed: schema is not draft-07")
if schema.get("id") != "LDR_DLL_NOTIFICATION_LOCK_UNION_GATE":
    raise SystemExit("SREV-312 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ldr.c":
    raise SystemExit("SREV-312 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ldr_LdrDllNotification owns Windows loader notification reason dispatch",
    "LDR_DLL_NOTIFICATION_REASON_LOADED routes only through NotificationData->Loaded",
    "LDR_DLL_NOTIFICATION_REASON_UNLOADED routes only through NotificationData->Unloaded",
    "LdrLockLoaderLock status must be tested with NT_SUCCESS before unlocking its cookie",
    "not Ldr_Dlls callback table policy",
]:
    require(contracts, term, "schema")

ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-312-ldr-dll-notification-lock-union-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-312.md").read_text()

for term in [
    "#define LDR_DLL_NOTIFICATION_REASON_LOADED 1",
    "#define LDR_DLL_NOTIFICATION_REASON_UNLOADED 2",
    "typedef union _LDR_DLL_NOTIFICATION_DATA",
    "LDR_DLL_LOADED_NOTIFICATION_DATA Loaded;",
    "LDR_DLL_UNLOADED_NOTIFICATION_DATA Unloaded;",
]:
    require(ldr, term, "loader notification declarations")

start = ldr.index("void CALLBACK Ldr_LdrDllNotification(")
end = ldr.index("//_FX NTSTATUS Ldr_LdrRegisterDllNotification", start)
func = ldr[start:end]

for term in [
    "if (NotificationReason == LDR_DLL_NOTIFICATION_REASON_LOADED)",
    "status = __sys_LdrLockLoaderLock(0, NULL, &LdrCookie);",
    "if (NT_SUCCESS(status)) {",
    "Ldr_MyDllCallbackNew(NotificationData->Loaded.BaseDllName->Buffer, (HMODULE)NotificationData->Loaded.DllBase, TRUE);",
    "__sys_LdrUnlockLoaderLock(0, LdrCookie);",
    "else if (NotificationReason == LDR_DLL_NOTIFICATION_REASON_UNLOADED)",
    "Ldr_MyDllCallbackNew(NotificationData->Unloaded.BaseDllName->Buffer,  (HMODULE)NotificationData->Unloaded.DllBase, FALSE);",
]:
    require(func, term, "Ldr_LdrDllNotification")

lock = func.index("status = __sys_LdrLockLoaderLock")
gate = func.index("if (NT_SUCCESS(status))", lock)
callback = func.index("NotificationData->Loaded.DllBase", gate)
unlock = func.index("__sys_LdrUnlockLoaderLock", callback)
if not lock < gate < callback < unlock:
    raise SystemExit("SREV-312 failed: loader-lock gate ordering is wrong")

for stale in [
    "if (NotificationReason == 1)",
    "else if (NotificationReason == 2)",
    "NotificationData->Unloaded.BaseDllName->Buffer,  (HMODULE)NotificationData->Loaded.DllBase",
]:
    reject(func, stale, "loader notification dispatch")

for term in [
    "{ L\"msi.dll\",               Scm_MsiDll,",
    "{ L\"winspool.drv\",          Gdi_Init_Spool,",
    "{ L\"hnetcfg.dll\",           HNet_Init,",
    "{ L\"winnsi.dll\",            NsiRpc_Init,",
    "{ L\"dwrite.dll\",            Scm_DWriteDll,",
    "{ L\"ntmarta.dll\",           Ntmarta_Init,",
    "Ldr_LoadSkipList();",
    "dll->state |= 2;",
    "ok = dll->init_func(ImageBase);",
    "SbieDll_UnHookModule(ImageBase);",
]:
    require(ldr, term, "unchanged callback-table topology")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "LDR_DLL_NOTIFICATION_LOCK_UNION_GATE",
    "NotificationData->Unloaded.DllBase",
    "NT_SUCCESS(status)",
    "Runtime gate: Windows 8.1+ DLL load/unload smoke",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-312: Ldr DLL Notification Lock And Union Gate",
    "LDR_DLL_NOTIFICATION_LOCK_UNION_GATE",
    "srev-312-ldr-dll-notification-lock-union-gate.schema.json",
    "Sandboxie/core/dll/ldr.c",
    "Ldr_LdrDllNotification",
    "LdrRegisterDllNotification",
    "LdrDllNotification",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-312 source gate passed")
