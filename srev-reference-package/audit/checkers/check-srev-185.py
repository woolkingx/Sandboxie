#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-185 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-185 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-185 failed: {label}")


schema = json.loads((ROOT / "docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-185 failed: schema is not draft-07")
if schema.get("id") != "DLL_LSA_UNTRUSTED_FALLBACK_CONTRACT":
    raise SystemExit("SREV-185 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/lsa.c":
    raise SystemExit("SREV-185 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "lsa.c owns DLL-side interception",
    "LsaRegisterLogonProcess returns NTSTATUS",
    "falls back to LsaConnectUntrusted",
    "LsaConnectUntrusted returns NTSTATUS not ULONG",
    "fallback target must be resolved before installing",
    "SBIEDLL_HOOK owns detour install",
    "Secur32.dll is used before Windows 7",
    "does not change LSA endpoint policy",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

lsa_c = (ROOT / "Sandboxie/core/dll/lsa.c").read_text()
ldr_c = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
sbiedll_h = (ROOT / "Sandboxie/core/dll/sbiedll.h").read_text()
spec = (ROOT / "docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-185.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef NTSTATUS (*P_LsaConnectUntrusted)(HANDLE *LsaHandle);",
    "typedef NTSTATUS (*P_LsaRegisterLogonProcess)(",
    "__sys_LsaConnectUntrusted = (P_LsaConnectUntrusted)",
    "Ldr_GetProcAddrNew(DllName, L\"LsaConnectUntrusted\",\"LsaConnectUntrusted\");",
    "LsaRegisterLogonProcess = (P_LsaRegisterLogonProcess)",
    "Ldr_GetProcAddrNew(DllName, L\"LsaRegisterLogonProcess\",\"LsaRegisterLogonProcess\");",
    "if (! __sys_LsaConnectUntrusted)",
    "return FALSE;",
    "SBIEDLL_HOOK(Lsa_,LsaRegisterLogonProcess);",
    "NTSTATUS status = __sys_LsaRegisterLogonProcess(",
    "if (! NT_SUCCESS(status))",
    "status = __sys_LsaConnectUntrusted(LsaHandle);",
    "return Lsa_Init_Common(DllName_secur32, module);",
    "return Lsa_Init_Common(DllName_sspicli, module);",
]:
    require(lsa_c, term, "lsa.c source")

reject(lsa_c, "typedef ULONG (*P_LsaConnectUntrusted)", "stale LsaConnectUntrusted return type")
assert_before(
    lsa_c,
    "fallback pointer gate before hook install",
    "if (! __sys_LsaConnectUntrusted)",
    "SBIEDLL_HOOK(Lsa_,LsaRegisterLogonProcess);",
)

for term in [
    "{ L\"secur32.dll\",           Lsa_Init_Secur32",
    "{ L\"sspicli.dll\",           Lsa_Init_SspiCli",
]:
    require(ldr_c, term, "loader module dispatch")

for term in [
    "#define SBIEDLL_HOOK(pfx,proc)",
    "SbieDll_Hook(#proc, proc, pfx##proc, module);",
    "if (! __sys_##proc) return FALSE;",
]:
    require(sbiedll_h, term, "hook macro")

for term in [
    "LsaConnectUntrusted",
    "LsaRegisterLogonProcess",
    "NTSTATUS",
    "Secur32",
    "SspiCli",
    "KPATH-004",
    "KPATH-006",
    "Sandboxie/core/dll/lsa.c",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-185",
    "owner: Sandboxie/core/dll/lsa.c",
    "spec: docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.md",
    "schema: docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.schema.json",
    "checker: docs/plan/check-srev-185.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-185: DLL LSA Untrusted Fallback Contract",
    "DLL_LSA_UNTRUSTED_FALLBACK_CONTRACT",
    "Sandboxie/core/dll/lsa.c",
    "P_LsaConnectUntrusted",
    "NTSTATUS",
    "LsaConnectUntrusted",
    "LsaRegisterLogonProcess",
]:
    require(ledger, term, "combined ledger")

print("SREV-185 schema/source gate passed")
