#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-106 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-106 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-106-low-inject-arm64ec-syscall-entrypoint.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-106 failed: schema is not draft-07")
if schema.get("id") != "LOW_INJECT_ARM64EC_SYSCALL_ENTRYPOINT":
    raise SystemExit("SREV-106 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "ARM64EC allows x64 and Arm64EC code to interoperate",
    "call checkers and exit thunks",
    "fast-forward sequences are small x64 functions",
    "ordinary ARM64EC exports may be FFS-resolved",
    "native system services use Nt and Zw entrypoints",
    "routed through local syscall-wrapper state",
    "WOW64 injection resolves 32-bit ntdll Nt* exports",
    "native and ARM64EC injection use pre-captured native or EC entrypoints",
    "NtDeviceIoControlFile may point to the EC wrapper",
    "must not change injection pointer assignments",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/low/inject.c").read_text()
lowdata = (ROOT / "Sandboxie/core/low/lowdata.h").read_text()
init = (ROOT / "Sandboxie/core/low/init.c").read_text()
ll_inject = (ROOT / "Sandboxie/core/dll/lowlevel_inject.c").read_text()
hook_util = (ROOT / "Sandboxie/common/hook_util.c").read_text()
spec = (ROOT / "docs/plan/srev-106-low-inject-arm64ec-syscall-entrypoint.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "if (data->flags.is_wow64)",
    "inject->NtProtectVirtualMemory = (ULONG_PTR)FindDllExport(ntdll_base,",
    "inject->NtRaiseHardError = (ULONG_PTR)FindDllExport(ntdll_base,",
    "inject->NtDeviceIoControlFile = (ULONG_PTR)FindDllExport(ntdll_base,",
    "ARM64EC ordinary exports can be FFS-resolved to native EC targets.",
    "Nt* syscall exports are routed through SbieLow syscall-wrapper state;",
    "keep the pre-captured native/EC entrypoints for injection-time calls.",
    "inject->NtProtectVirtualMemory = data->NativeNtProtectVirtualMemory;",
    "inject->NtRaiseHardError = data->NativeNtRaiseHardError;",
    "inject->NtDeviceIoControlFile = data->NtDeviceIoControlFile;",
    "if (inject->LdrLoadDll && data->flags.is_arm64ec)",
    "Hook_GetFFSTarget((UCHAR*)inject->LdrLoadDll)",
    "Hook_GetFFSTarget((UCHAR*)inject->LdrGetProcAddr)",
]:
    require(source, term, "inject.c source shape")

branch_start = source.index("if (data->flags.is_wow64)")
branch_end = source.index("inject->api_device_handle = data->api_device_handle;", branch_start)
branch = source[branch_start:branch_end]
if branch.index("FindDllExport(ntdll_base") > branch.index("data->NativeNtProtectVirtualMemory"):
    raise SystemExit("SREV-106 failed: native entrypoint branch appears before WOW64 export branch")

for term in [
    "NativeNtProtectVirtualMemory",
    "NativeNtRaiseHardError",
    "NtDeviceIoControlFile; // for ARM64",
    "NATIVE_FUNCTION_NAMES",
]:
    require(lowdata, term, "lowdata.h shape")

for term in [
    "void* EcExitThunkPtr = SbieDll_GetEcExitThunkPtr(HandleStubHijack);",
    "*(ULONG64*)SyscallPtrEC = (ULONG64)EcExitThunkPtr;",
    "lowdata.NativeNtProtectVirtualMemory = (ULONG64)GetProcAddress((HMODULE)lowdata.ntdll_base, \"NtProtectVirtualMemory\");",
    "lowdata.NativeNtRaiseHardError = (ULONG64)GetProcAddress((HMODULE)lowdata.ntdll_base, \"NtRaiseHardError\");",
]:
    require(ll_inject, term, "lowlevel_inject.c shape")

for term in [
    "NtDeviceIoControlFileEC",
    "WriteMemorySafe(data, &data->NtDeviceIoControlFile, sizeof(ULONG64), &pNtDeviceIoControlFileEC);",
    "WriteMemorySafe(data, &DeviceIoControlSvc, sizeof(ULONG), &data->NtDeviceIoControlFile_code[0]);",
    "WriteMemorySafe(data, &EcExitThunkPtr, sizeof(UINT_PTR), &pEcExitThunkPtr);",
]:
    require(init, term, "init.c EC syscall-wrapper shape")

for term in [
    "Hook_GetFFSTargetOld",
    "Hook_GetFFSTargetNew",
    "return the address of the target native function",
]:
    require(hook_util, term, "hook_util.c FFS shape")

reject(source, "however this does not work for syscalls", "inject.c")

for term in [
    "### SREV-106: Low Inject ARM64EC Syscall Entrypoint",
    "LOW_INJECT_ARM64EC_SYSCALL_ENTRYPOINT",
    "srev-106-low-inject-arm64ec-syscall-entrypoint.schema.json",
    "Comment-only source clarification",
    "Sandboxie/core/low/inject.c",
]:
    require(ledger, term, "ledger")

print("SREV-106 schema/source gate passed")
