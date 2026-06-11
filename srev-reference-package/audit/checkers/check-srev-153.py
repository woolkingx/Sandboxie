#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-153 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-153 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-153-spooler-counted-port-name.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-153 failed: schema is not draft-07")
if schema.get("id") != "IPC_SPOOLER_COUNTED_PORT_NAME":
    raise SystemExit("SREV-153 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "OBJECT_NAME_INFORMATION.Name is a counted UNICODE_STRING",
    "UNICODE_STRING.Length is a byte count",
    "not authorize C-string scans over Name->Name.Buffer",
    "Spooler endpoint matching must compare counted strings with RtlEqualUnicodeString",
    "Windows 8.1 dynamic spooler port gate still accepts only the cached dynamic spooler port name",
    "Vista fallback still accepts only RPC Control spoolss",
    "does not change KPATH-006 RPC payload capture",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/ipc_spl.c").read_text()
spec = (ROOT / "docs/plan/srev-153-spooler-counted-port-name.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-153.md").read_text()
kpath006 = (ROOT / "docs/plan/2026-05-27-sandboxie-kernel-path-audit.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static BOOLEAN Ipc_Spl_MatchPortName(",
    "const UNICODE_STRING* PortName, const WCHAR* ExpectedName",
    "UNICODE_STRING expected;",
    "RtlInitUnicodeString(&expected, ExpectedName);",
    "return RtlEqualUnicodeString(PortName, &expected, TRUE);",
    "Name->Name.Length < 13 * sizeof(WCHAR)",
    "Ipc_Dynamic_Ports.pSpoolerPort",
    "Ipc_Spl_MatchPortName(&Name->Name, Ipc_Dynamic_Ports.pSpoolerPort->wstrPortName)",
    "Ipc_Spl_MatchPortName(&Name->Name, L\"\\\\RPC Control\\\\spoolss\")",
    "Ipc_GetRpcMsgId(proc, L\"\\\\RPC Control\\\\spoolss\", ptr, len, &uMsg)",
]:
    require(source, term, "ipc_spl.c")

reject(source, "_wcsicmp(Name->Name.Buffer", "ipc_spl.c C-string object-name compare")

for term in [
    "case 0x05:",
    "case 0x06:",
    "case 0x0D:",
    "case 0x0E:",
    "case 0x1B:",
    "case 0x1E:",
    "case 0x25:",
    "case 0x3D:",
    "case 0x59:",
    "case 0x6C:",
    "Log_Debug_Msg(mon_type, msg_str, L\"\\\\RPC Control\\\\spoolss\")",
]:
    require(source, term, "spooler opnum policy preservation")

for term in [
    "Ipc_GetRpcMsgId",
    "trace-only capture",
    "not a final parser",
]:
    require(kpath006, term, "KPATH-006 note")

for term in [
    "### SREV-153: Spooler Counted Port Name",
    "IPC_SPOOLER_COUNTED_PORT_NAME",
    "srev-153-spooler-counted-port-name.schema.json",
    "Sandboxie/core/drv/ipc_spl.c",
    "Ipc_Spl_MatchPortName",
    "RtlEqualUnicodeString",
    "OBJECT_NAME_INFORMATION.Name",
    "KPATH-006",
    "MS-RPRN",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-153 schema/source gate passed")
