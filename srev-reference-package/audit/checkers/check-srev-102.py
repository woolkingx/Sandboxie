#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-102 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-102-syscall64-private-table-scanner-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-102 failed: schema is not draft-07")
if schema.get("id") != "SYSCALL64_PRIVATE_TABLE_SCANNER_BOUNDARY":
    raise SystemExit("SREV-102 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "exported KeServiceDescriptorTable when available before private pattern scanning",
    "disabled x64 0x40 / 0xC0 spacing check",
    "KVA Shadow / KB4056892 changed x64 kernel-entry",
    "implementation details are subject to change",
    "ShadowTable->Addrs against MasterTable->Addrs",
    "ARM64 MasterTable lookup uses an ADRP / ADD pattern",
    "ARM64 FilterTable lookup remains fail-closed",
    "does not change service table offsets, pattern scanner behavior, or syscall dispatch",
]:
    require(contracts, term, "schema")

syscall64 = (ROOT / "Sandboxie/core/drv/syscall_64.c").read_text()
spec = (ROOT / "docs/plan/srev-102-syscall64-private-table-scanner-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "RtlInitUnicodeString(&uni, L\"KeServiceDescriptorTable\")",
    "MasterTable = MmGetSystemRoutineAddress(&uni)",
    "RtlInitUnicodeString(&uni, L\"KeAddSystemServiceTable\")",
    "ptr = (UCHAR*)MmGetSystemRoutineAddress(&uni)",
    "Historical spacing check disabled: KVA Shadow / KB4056892 changed",
    "private invariant is not legal",
    "//if (        (ofs32a - ofs32b != 0x40 && ofs32b - ofs32a != 0x40)",
    "ShadowTable->Addrs != MasterTable->Addrs",
    "IS_ADRP(adrp)",
    "IS_ADD(add)",
    "ARM64 filter-table lookup remains fail-closed",
    "version-gated",
    "KeAddSystemServiceTable pattern",
    "return 0;",
]:
    require(syscall64, term, "syscall_64.c source shape")

for stale in [
    "This code block is broken by KB4056892",
    "// TODO",
]:
    if stale in syscall64:
        raise SystemExit(f"SREV-102 failed: stale wording remains {stale!r}")

for term in [
    "CVE-2017-5754",
    "Meltdown",
    "KVA Shadow",
    "subject to change",
    "Windows ARM64 ABI",
    "fail-closed",
    "No service table offsets",
]:
    require(spec, term, "spec shape")

for term in [
    "### SREV-102: Syscall64 Private Table Scanner Boundary",
    "SYSCALL64_PRIVATE_TABLE_SCANNER_BOUNDARY",
    "srev-102-syscall64-private-table-scanner-boundary.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-102 schema/source gate passed")
