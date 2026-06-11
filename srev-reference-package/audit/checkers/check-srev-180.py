#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-180 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-180 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-180 failed: {label}")


def function_slice(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


schema = json.loads(
    (ROOT / "docs/plan/srev-180-syscall32-shadow-table-candidate-read-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-180 failed: schema is not draft-07")
if schema.get("id") != "SYSCALL32_SHADOW_TABLE_CANDIDATE_READ_BOUNDARY":
    raise SystemExit("SREV-180 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetShadowTableAddress owns the 32-bit private shadow service-table fallback scanner",
    "untrusted candidate table pointers",
    "MmIsAddressValid is only a preliminary nonpaged-address check",
    "comparison must be inside a structured exception boundary",
    "rejects NULL candidates and KeServiceDescriptorTable itself",
    "preserves the existing 1024-byte scan window",
]:
    require(contracts, term, "schema contracts")

syscall32 = (ROOT / "Sandboxie/core/drv/syscall_32.c").read_text()
spec = (ROOT / "docs/plan/srev-180-syscall32-shadow-table-candidate-read-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-180.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

helper = function_slice(
    syscall32,
    "static BOOLEAN Syscall_IsShadowTableCandidate",
    "PSYSTEM_SERVICE_TABLE GetShadowTableAddress",
)
scanner = function_slice(
    syscall32,
    "PSYSTEM_SERVICE_TABLE GetShadowTableAddress",
    "//---------------------------------------------------------------------------\n// Syscall_GetServiceTable",
)

for term in [
    "BOOLEAN match = FALSE;",
    "if ((!pTable) || ((PVOID)pTable == (PVOID)&KeServiceDescriptorTable))",
    "__try {",
    "if (MmIsAddressValid(pTable))",
    "memcmp(",
    "pTable, &KeServiceDescriptorTable,",
    "sizeof(SYSTEM_SERVICE_TABLE)) == 0",
    "} __except (EXCEPTION_EXECUTE_HANDLER) {",
    "match = FALSE;",
    "return match;",
]:
    require(helper, term, "guarded candidate helper")

for term in [
    "PUCHAR pCheckByte = (PUCHAR)KeAddSystemServiceTable;",
    "for (i = 0; i < 1024; i++)",
    "pTable = *(PSYSTEM_SERVICE_TABLE*)pCheckByte;",
    "if (!Syscall_IsShadowTableCandidate(pTable))",
    "pCheckByte++;",
    "pTable = NULL;",
]:
    require(scanner, term, "scanner shape")

reject(scanner, "memcmp(pTable, &KeServiceDescriptorTable", "direct scanner memcmp")
reject(scanner, "!MmIsAddressValid(pTable) ||", "old MmIsAddressValid-only predicate")
assert_before(
    helper,
    "identity rejected before guarded comparison",
    "if ((!pTable) || ((PVOID)pTable == (PVOID)&KeServiceDescriptorTable))",
    "__try {",
)

for term in [
    "We do not recommend using this function",
    "Even if MmIsAddressValid returns TRUE",
    "must handle raised exceptions",
    "__try",
    "private scanner fallback",
    "No 32-bit service-table offsets",
]:
    require(spec, term, "spec shape")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-180",
    "owner: Sandboxie/core/drv/syscall_32.c",
    "checker: docs/plan/check-srev-180.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-180: Syscall32 Shadow Table Candidate Read Boundary",
    "SYSCALL32_SHADOW_TABLE_CANDIDATE_READ_BOUNDARY",
    "Sandboxie/core/drv/syscall_32.c",
    "Syscall_IsShadowTableCandidate",
    "GetShadowTableAddress",
    "MmIsAddressValid",
]:
    require(ledger, term, "ledger")

print("SREV-180 schema/source gate passed")
