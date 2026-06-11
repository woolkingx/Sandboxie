#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-119 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-119 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-119-low-init-protect-write-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-119 failed: schema is not draft-07")
if schema.get("id") != "LOW_INIT_PROTECT_WRITE_GATE":
    raise SystemExit("SREV-119 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "PAGE_EXECUTE_READWRITE through NtProtectVirtualMemory must check NTSTATUS",
    "OldProtect is initialized before each writable-protection attempt",
    "WriteMemorySafe fails closed",
    "InitSyscalls skips the current syscall export",
    "DisableCHPE returns before trampoline or target-detour byte writes",
    "does not change syscall selection detour bytes",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/low/init.c").read_text()
spec = (ROOT / "docs/plan/srev-119-low-init-protect-write-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
win32_ntddk = (ROOT / "Sandboxie/common/win32_ntddk.h").read_text()
lowdata = (ROOT / "Sandboxie/core/low/lowdata.h").read_text()
srev106 = (ROOT / "docs/plan/srev-106-low-inject-arm64ec-syscall-entrypoint.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "__declspec(dllimport) NTSTATUS __stdcall NtProtectVirtualMemory(",
    "OUT PULONG OldProtect",
    "#define NT_SUCCESS(Status)",
]:
    require(win32_ntddk, term, "local NtProtectVirtualMemory typedef")

for term in [
    "NtDeviceIoControlFileEC",
    "EcExitThunkPtr",
]:
    require(srev106, term, "SREV-106 preserved context")
require(lowdata, "NativeNtProtectVirtualMemory", "lowdata preserved native entrypoint")

protect_writes = re.findall(
    r"status = SBIELOW_CALL\(NtProtectVirtualMemory\)\(\n"
    r"\s*NtCurrentProcess\(\), &RegionBase, &RegionSize,\n"
    r"\s*PAGE_EXECUTE_READWRITE, &OldProtect\);",
    source,
)
if len(protect_writes) != 4:
    raise SystemExit(f"SREV-119 failed: expected 4 checked PAGE_EXECUTE_READWRITE gates, found {len(protect_writes)}")

write_memory = source[source.index("_FX void WriteMemorySafe"):source.index("//---------------------------------------------------------------------------\n// PrepSyscalls")]
for term in [
    "NTSTATUS status;",
    "ULONG OldProtect = 0;",
    "status = SBIELOW_CALL(NtProtectVirtualMemory)(",
    "PAGE_EXECUTE_READWRITE, &OldProtect);",
    "if (! NT_SUCCESS(status))\n        return;",
    "case 8: *(ULONG64*)Address = *(ULONG64*)Data;",
    "OldProtect, &OldProtect);",
]:
    require(write_memory, term, "WriteMemorySafe protect gate")
if write_memory.index("if (! NT_SUCCESS(status))") > write_memory.index("switch (Size)"):
    raise SystemExit("SREV-119 failed: WriteMemorySafe writes before protection gate")

init_syscalls = source[source.index("_FX void InitSyscalls"):source.index("#ifdef _M_ARM64\n\n//---------------------------------------------------------------------------\n// MyImageOptionsEx")]
for term in [
    "ULONG OldProtect = 0;",
    "NTSTATUS status;",
    "OldProtect = 0;",
    "status = SBIELOW_CALL(NtProtectVirtualMemory)(",
    "if (! NT_SUCCESS(status)) {\n            SyscallPtr += 2;\n            continue;\n        }",
    "SyscallNum = SyscallPtr[0];",
    "SBIELOW_CALL(NtFlushInstructionCache)(",
]:
    require(init_syscalls, term, "InitSyscalls protect gate")
if init_syscalls.index("if (! NT_SUCCESS(status))") > init_syscalls.index("SyscallNum = SyscallPtr[0];"):
    raise SystemExit("SREV-119 failed: InitSyscalls writes before protection gate")

disable_chpe = source[source.index("_FX void DisableCHPE"):source.index("#endif\n\n\n#ifdef _WIN64")]
for term in [
    "ULONG OldProtect = 0;",
    "NTSTATUS status;",
    "status = SBIELOW_CALL(NtProtectVirtualMemory)(",
    "if (! NT_SUCCESS(status))\n        return;",
    "memcpy(data->RtlImageOptionsEx_tramp, RtlImageOptionsEx, DetourSize);",
    "OldProtect = 0;",
    "aCode = (ULONG*)RtlImageOptionsEx;",
    "SBIELOW_CALL(NtFlushInstructionCache)(",
]:
    require(disable_chpe, term, "DisableCHPE protect gate")
first_gate = disable_chpe.index("if (! NT_SUCCESS(status))")
trampoline_write = disable_chpe.index("memcpy(data->RtlImageOptionsEx_tramp")
second_gate = disable_chpe.rindex("if (! NT_SUCCESS(status))")
target_write = disable_chpe.index("aCode = (ULONG*)RtlImageOptionsEx;")
if first_gate > trampoline_write:
    raise SystemExit("SREV-119 failed: DisableCHPE trampoline writes before protection gate")
if second_gate > target_write:
    raise SystemExit("SREV-119 failed: DisableCHPE target writes before protection gate")

reject(source, "ULONG OldProtect;\n\n    SBIELOW_CALL(NtProtectVirtualMemory)", "unchecked local protect-write pattern")

for term in [
    "### SREV-119: Low Init Protect Write Gate",
    "LOW_INIT_PROTECT_WRITE_GATE",
    "srev-119-low-init-protect-write-gate.schema.json",
    "Sandboxie/core/low/init.c",
    "NtProtectVirtualMemory",
    "PAGE_EXECUTE_READWRITE",
    "OldProtect",
    "WriteMemorySafe",
    "InitSyscalls",
    "DisableCHPE",
]:
    require(ledger, term, "ledger")

print("SREV-119 schema/source gate passed")
