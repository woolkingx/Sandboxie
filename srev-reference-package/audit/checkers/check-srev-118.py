#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-118 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-118 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-118-ipc-lsa-counted-port-name.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-118 failed: schema is not draft-07")
if schema.get("id") != "IPC_LSA_COUNTED_PORT_NAME":
    raise SystemExit("SREV-118 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "OBJECT_NAME_INFORMATION.Name is a counted UNICODE_STRING",
    "UNICODE_STRING.Length is a byte count",
    "not C-string scans over Name->Name.Buffer",
    "continues to accept only LsaAuthenticationPort",
    "continues to accept only RPC Control LSARPC_ENDPOINT",
    "does not change MS-LSAD opnum policy",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/ipc_lsa.c").read_text()
spec = (ROOT / "docs/plan/srev-118-ipc-lsa-counted-port-name.md").read_text()
ledger = read_combined_ledger(ROOT)
kpath004 = (ROOT / "docs/plan/kpath-004-lsad-spec.md").read_text()
kpath006 = (ROOT / "docs/plan/2026-05-27-sandboxie-kernel-path-audit.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static BOOLEAN Ipc_Lsa_MatchPortName(",
    "const UNICODE_STRING* PortName, const WCHAR* ExpectedName",
    "UNICODE_STRING expected;",
    "RtlInitUnicodeString(&expected, ExpectedName);",
    "return RtlEqualUnicodeString(PortName, &expected, TRUE);",
    "Name->Name.Length == 22 * sizeof(WCHAR)",
    "Name->Name.Length == 23 * sizeof(WCHAR)",
    "Name->Name.Length == 28 * sizeof(WCHAR)",
    "Ipc_Lsa_MatchPortName(&Name->Name, L\"\\\\LsaAuthenticationPort\")",
    "Ipc_Lsa_MatchPortName(&Name->Name, L\"\\\\RPC Control\\\\lsasspirpc\")",
    "Ipc_Lsa_MatchPortName(&Name->Name, L\"\\\\RPC Control\\\\LSARPC_ENDPOINT\")",
    "Ipc_GetRpcMsgId(proc, L\"\\\\RPC Control\\\\LSARPC_ENDPOINT\", ptr, len, &uMsg)",
]:
    require(source, term, "ipc_lsa.c")

reject(source, "_wcsicmp(Name->Name.Buffer", "ipc_lsa.c C-string object-name compare")

for term in [
    "case 0x10:",
    "case 0x1C:",
    "case 0x1D:",
    "case 0x1E:",
    "case 0x22:",
    "case 0x2A:",
    "case 0x2B:",
    "case 0x88:",
    "case 0x89:",
    "case 0x8A:",
    "case 0x8B:",
    "case 0x8C:",
    "case 0x8D:",
]:
    require(source, term, "KPATH-004 LSAD opnum preservation")

for term in [
    "LsarOpenPolicy",
    "DesiredAccess",
    "deny known secret/private-data opnums early",
]:
    require(kpath004, term, "KPATH-004 spec")

for term in [
    "Ipc_GetRpcMsgId",
    "trace-only capture",
    "not a final parser",
]:
    require(kpath006, term, "KPATH-006 note")

for term in [
    "### SREV-118: IPC LSA Counted Port Name",
    "IPC_LSA_COUNTED_PORT_NAME",
    "srev-118-ipc-lsa-counted-port-name.schema.json",
    "Sandboxie/core/drv/ipc_lsa.c",
    "Ipc_Lsa_MatchPortName",
    "RtlEqualUnicodeString",
    "OBJECT_NAME_INFORMATION.Name",
    "KPATH-004",
    "KPATH-006",
]:
    require(ledger, term, "ledger")

print("SREV-118 schema/source gate passed")
