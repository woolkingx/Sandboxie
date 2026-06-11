#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-201 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-201 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-201-netapi-slave-drive-command-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-201 failed: schema is not draft-07")
if schema.get("id") != "NETAPI_SLAVE_DRIVE_COMMAND_CONTRACT":
    raise SystemExit("SREV-201 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/netapiserver.h":
    raise SystemExit("SREV-201 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/svc/netapiserver.cpp":
    raise SystemExit("SREV-201 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "LaunchSlave validates the local device drive letter before creating the helper command",
    "RunSlave validates the command drive letter before DefineDosDevice",
    "RunSlave requires a command terminator after the drive letter",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/svc/netapiserver.cpp").read_text()
header = (ROOT / "Sandboxie/core/svc/netapiserver.h").read_text()
spec = (ROOT / "docs/plan/srev-201-netapi-slave-drive-command-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-201.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(header, "static void RunSlave(const WCHAR *cmdline);", "header owner declaration")

for term in [
    "static BOOLEAN NetApiServer_IsDriveLetter(WCHAR ch)",
    "return ((ch >= L'A' && ch <= L'Z') || (ch >= L'a' && ch <= L'z'));",
    "static BOOLEAN NetApiServer_IsUseCommandTerminator(WCHAR ch)",
    "return (ch == L'\\0' || ch == L' ' || ch == L'\\t' || ch == L'\"');",
]:
    require(src, term, "drive command helper")

launch = between(
    src,
    "void NetApiServer::LaunchSlave(",
    "//---------------------------------------------------------------------------\n// RunSlave",
)
for term in [
    "if (len != 2 || drive[1] != L':' ||",
    "! NetApiServer_IsDriveLetter(drive[0]))",
    "return;",
    "wsprintf(cmdline, L\"%s_NetProxy:Use=%c\", SANDBOXIE, drive[0]);",
]:
    require(launch, term, "LaunchSlave drive gate")

run = between(
    src,
    "void NetApiServer::RunSlave(",
    "ExitProcess(0);",
)
for term in [
    "if (cmdline && wmemcmp(cmdline, L\":Use=\", 5) == 0) {",
    "WCHAR drive = towupper(cmdline[5]);",
    "if (NetApiServer_IsDriveLetter(drive) &&",
    "NetApiServer_IsUseCommandTerminator(cmdline[6])) {",
    "device[0] = drive;",
    "DefineDosDevice(DDD_LUID_BROADCAST_DRIVE, device, NULL);",
]:
    require(run, term, "RunSlave drive gate")

if not run.index("NetApiServer_IsDriveLetter(drive)") < run.index("DefineDosDevice("):
    raise SystemExit("SREV-201 failed: DefineDosDevice before drive-letter gate")
if not run.index("NetApiServer_IsUseCommandTerminator(cmdline[6])") < run.index("DefineDosDevice("):
    raise SystemExit("SREV-201 failed: DefineDosDevice before command terminator gate")
reject(run, "device[0] = towupper(cmdline[5]);", "ungated direct drive assignment")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-201",
    "owner: Sandboxie/core/svc/netapiserver.h",
    "implementation: Sandboxie/core/svc/netapiserver.cpp",
    "spec: docs/plan/srev-201-netapi-slave-drive-command-contract.md",
    "schema: docs/plan/srev-201-netapi-slave-drive-command-contract.schema.json",
    "checker: docs/plan/check-srev-201.py",
    "patched source-level after official NetAPI/DefineDosDevice shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-201 source gate passed")
