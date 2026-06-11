#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-257 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-257 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-257-custom-avast-trampoline-publish-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-257 failed: schema is not draft-07")
if schema.get("id") != "CUSTOM_AVAST_TRAMPOLINE_PUBLISH_GATE":
    raise SystemExit("SREV-257 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "generated executable trampoline",
    "local unpublished pointer",
    "flushed before publication",
    "Allocation failure returns the native lookup status",
    "does not change hook selection",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
spec = (ROOT / "docs/plan/srev-257-custom-avast-trampoline-publish-gate.md").read_text()
srev_058 = (ROOT / "docs/plan/srev-058-dllhook-instruction-cache.md").read_text()
srev_247 = (ROOT / "docs/plan/srev-247-dllhook-wow64-stub-publish-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-257.md").read_text()

start = source.index("_FX NTSTATUS Custom_Avast_SnxHk_LdrGetProcedureAddress(")
end = source.index("// Custom_Avast_SnxHk", start)
avast = source[start:end]

for term in [
    "ModuleHandle == Dll_Ntdll",
    "ProcName->Length == 21",
    "memcmp(ProcName->Buffer, \"NtDeviceIoControlFile\", 21) == 0",
    "static UCHAR *code = 0;",
    "UCHAR *new_code = Dll_AllocCode128();",
    "if (! new_code)\n                return status;",
    "*(USHORT *)new_code = 0xB848;",
    "*(ULONG64 *)(new_code + 2) = *Address;",
    "*(USHORT *)(new_code + 10) = 0xE0FF;",
    "*new_code = 0xB8;",
    "*(ULONG *)(new_code + 1) = *Address;",
    "*(USHORT *)(new_code + 5) = 0xE0FF;",
    "FlushInstructionCache(GetCurrentProcess(), new_code, 12);",
    "code = new_code;",
    "*Address = (ULONG_PTR)code;",
]:
    require(avast, term, "Custom_Avast_SnxHk_LdrGetProcedureAddress")

if avast.index("FlushInstructionCache(GetCurrentProcess(), new_code, 12);") > avast.index("code = new_code;"):
    raise SystemExit("SREV-257 failed: flush must happen before static publication")
if avast.index("code = new_code;") > avast.index("*Address = (ULONG_PTR)code;"):
    raise SystemExit("SREV-257 failed: static publication must happen before returned Address")

reject(avast, "\n            code = Dll_AllocCode128();", "Avast trampoline")
reject(avast, "*(USHORT *)code = 0xB848;", "Avast trampoline")
reject(avast, "*code = 0xB8;", "Avast trampoline")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Every user-mode executable-code mutation must be followed by",
    "FlushInstructionCache",
]:
    require(srev_058, term, "SREV-058 adjacency")

for term in [
    "write 13-byte transition stub",
    "FlushInstructionCache(stub, 13)",
]:
    require(srev_247, term, "SREV-247 adjacency")

for term in [
    "### SREV-257: Custom Avast Trampoline Publish Gate",
    "CUSTOM_AVAST_TRAMPOLINE_PUBLISH_GATE",
    "srev-257-custom-avast-trampoline-publish-gate.schema.json",
    "Sandboxie/core/dll/custom.c",
    "Custom_Avast_SnxHk_LdrGetProcedureAddress",
    "NtDeviceIoControlFile",
    "FlushInstructionCache",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-257 source gate passed")
