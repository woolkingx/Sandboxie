#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-132 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-132-low-arm64-entry-syscall-abi-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-132 failed: schema is not draft-07")
if schema.get("id") != "LOW_ARM64_ENTRY_SYSCALL_ABI_CONTRACT":
    raise SystemExit("SREV-132 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SystemServiceARM64 is an ARM64 syscall bridge that follows the Windows ARM64 volatile register and 16-byte stack-alignment contract",
    "SystemServiceARM64 spills original x0-x7 syscall arguments before repurposing x0-x7 for NtDeviceIoControlFile",
    "SystemServiceARM64 records the syscall index from x17 and the original argument-stack pointer in API_NUM_ARGS slots",
    "PrepSyscalls patches the ServiceDataPtr slot immediately before SystemServiceARM64 with the SBIELOW_DATA pointer",
    "ARM64EC PrepSyscalls routes data->NtDeviceIoControlFile to NtDeviceIoControlFileEC and copies the native svc instruction into DeviceIoControlSvc",
    "NtDeviceIoControlFileEC preserves the local handle-stub sentinel and branches through MyHandleStubHijack only when the emulator changes the sentinel",
]:
    require(contracts, term, "schema")

entry = (ROOT / "Sandboxie/core/low/entry_arm.asm").read_text()
init = (ROOT / "Sandboxie/core/low/init.c").read_text()
lowdata = (ROOT / "Sandboxie/core/low/lowdata.h").read_text()
spec = (ROOT / "docs/plan/srev-132-low-arm64-entry-syscall-abi-contract.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "EXPORT  SystemServiceARM64",
    "EXPORT  NtDeviceIoControlFileEC",
    "EXPORT  DeviceIoControlSvc",
    "EXPORT  EcExitThunkPtr",
    "EXPORT  DetourCodeARM64",
    "EXPORT  SbieLowData",
    "ServiceDataPtr\n    DCQ 0",
    "SystemServiceARM64 Proc",
]:
    require(entry, term, "entry_arm exports")

system_service = entry[
    entry.index("SystemServiceARM64 Proc"):
    entry.index(";----------------------------------------------------------------------------\n; MyHandleStubHijack")
]
for term in [
    "stp     x6, x7, [sp, #-0x10]!",
    "stp     x4, x5, [sp, #-0x10]!",
    "stp     x2, x3, [sp, #-0x10]!",
    "stp     x0, x1, [sp, #-0x10]!",
    "mov     x8, sp",
    "ldr     x9, ServiceDataPtr",
    "stp     fp, lr, [sp, #-0x10]!",
    "sub     sp, sp, (1 + 8 + 1 + 2 + 2) * 8",
    "add     x10, sp, (5*8)",
    "str     x17, [x10, (1*8)]",
    "str     x8, [x10, (2*8)]",
    "ldr     w8, [x9, (3*8+4)]",
    "str     x8, [x10, (0*8)]",
    "ldr     x0, [x9, (2*8)]",
    "ldr     w5, [x9, (3*8+0)]",
    "mov     x6, x10",
    "mov     x7, (8*8)",
    "add     x8, x9, #0xE8",
    "blr     x8",
    "add     sp, sp, (1 + 8 + 1 + 2 + 2) * 8",
    "add     sp, sp, #0x40",
    "ret",
]:
    require(system_service, term, "SystemServiceARM64")

ec_wrapper = entry[
    entry.index("NtDeviceIoControlFileEC PROC"):
    entry.index(";----------------------------------------------------------------------------\n; detour code loading SbieDll.dll")
]
for term in [
    "adrl x16, MyHandleStubHijackEnd",
    "str  x16, [sp]",
    "DeviceIoControlSvc",
    "svc  #0x07",
    "ldr  x9, [sp]",
    "subs x16, x16, x9",
    "b.ne MyHandleStubHijack",
    "movz x9, #0",
    "ret",
]:
    require(ec_wrapper, term, "NtDeviceIoControlFileEC")

for term in [
    "if (data->flags.is_arm64ec) {",
    "ULONG64 pNtDeviceIoControlFileEC = (ULONG64)&NtDeviceIoControlFileEC;",
    "WriteMemorySafe(data, &data->NtDeviceIoControlFile, sizeof(ULONG64), &pNtDeviceIoControlFileEC);",
    "WriteMemorySafe(data, &DeviceIoControlSvc, sizeof(ULONG), &data->NtDeviceIoControlFile_code[0]);",
    "UINT_PTR pEcExitThunkPtr = *(UINT_PTR*)((UINT_PTR)syscall_ec_data + syscall_ec_data[1] - 8);",
    "WriteMemorySafe(data, &EcExitThunkPtr, sizeof(UINT_PTR), &pEcExitThunkPtr);",
    "#ifdef _M_ARM64\n    -(LONG)sizeof(ULONG_PTR);",
    "WriteMemorySafe(data, ((UCHAR *)SystemService) + OFFSET_ULONG_PTR, sizeof(ULONG_PTR), &data);",
]:
    require(init, term, "PrepSyscalls")

for term in [
    "UCHAR   NtDeviceIoControlFile_code[NATIVE_FUNCTION_SIZE];     // offset 128",
    "ULONG64     RealNtDeviceIoControlFile;          // offset 224",
    "ULONG64     NtDeviceIoControlFile; // for ARM64 // offset 232",
    "#define SBIELOW_INJECTION_SECTION \".text\"",
    "#define SBIELOW_SYMBOL_SECTION     \"zzzz\"",
]:
    require(lowdata, term, "lowdata.h")

for term in [
    "### SREV-132: Low ARM64 Entry Syscall ABI Contract",
    "LOW_ARM64_ENTRY_SYSCALL_ABI_CONTRACT",
    "srev-132-low-arm64-entry-syscall-abi-contract.schema.json",
    "Sandboxie/core/low/entry_arm.asm",
    "Sandboxie/core/low/init.c",
    "Sandboxie/core/low/lowdata.h",
    "SystemServiceARM64",
    "NtDeviceIoControlFileEC",
    "DeviceIoControlSvc",
    "EcExitThunkPtr",
    "ARM64EC",
]:
    require(ledger, term, "ledger")

print("SREV-132 schema/source gate passed")
