#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-187 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-187 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-187 failed: {label}")


schema = json.loads(
    (ROOT / "docs/plan/srev-187-scm-event-log-fake-handle-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-187 failed: schema is not draft-07")
if schema.get("id") != "SCM_EVENT_LOG_FAKE_HANDLE_CONTRACT":
    raise SystemExit("SREV-187 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "event-log write suppression policy",
    "fake event-log handle",
    "must check RtlAnsiStringToUnicodeString",
    "ReportEventA/W consume a handle returned by RegisterEventSource",
    "DeregisterEventSource consumes a handle returned by RegisterEventSource",
    "ERROR_INVALID_HANDLE",
    "CloseEventLog remains separate",
    "pointer-to-string-array shape",
    "does not add host event-log brokering",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

scm_event = (ROOT / "Sandboxie/core/dll/scm_event.c").read_text()
scm_c = (ROOT / "Sandboxie/core/dll/scm.c").read_text()
spec = (ROOT / "docs/plan/srev-187-scm-event-log-fake-handle-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-187.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static HANDLE Scm_RegisterEventSourceW(WCHAR *ServerName, WCHAR *SourceName);",
    "static HANDLE Scm_RegisterEventSourceA(UCHAR *ServerName, UCHAR *SourceName);",
    "const WCHAR **Strings, void *RawData);",
    "const UCHAR **Strings, void *RawData);",
    "return (HANDLE)HANDLE_EVENT_LOG;",
    "NTSTATUS status;",
    "uni.Buffer = NULL;",
    "status = RtlAnsiStringToUnicodeString(&uni, &ansi, TRUE);",
    "if (! NT_SUCCESS(status))",
    "SetLastError(RtlNtStatusToDosError(status));",
    "return NULL;",
    "if (uni.Buffer)",
    "RtlFreeUnicodeString(&uni);",
]:
    require(scm_event, term, "scm_event.c source")

for term in [
    "_FX BOOL Scm_DeregisterEventSource(HANDLE hEventLog)",
    "_FX BOOL Scm_ReportEventW(",
    "_FX BOOL Scm_ReportEventA(",
    "if (hEventLog == (HANDLE)HANDLE_EVENT_LOG) {",
    "SetLastError(ERROR_INVALID_HANDLE);",
    "return FALSE;",
    "return __sys_CloseEventLog(hEventLog);",
]:
    require(scm_event, term, "fake-handle source")

assert_before(
    scm_event,
    "RegisterEventSourceA checks conversion before W path",
    "if (! NT_SUCCESS(status))",
    "handle = Scm_RegisterEventSourceW(NULL, uni.Buffer);",
)

reject(scm_event, "RtlAnsiStringToUnicodeString(&uni, &ansi, TRUE);\n\n    handle =", "unchecked A conversion")
reject(scm_event, "_FX BOOL Scm_DeregisterEventSource(HANDLE hEventLog)\n{\n    SetLastError(0);\n    return TRUE;\n}", "unconditional deregister success")

for term in [
    "#define HANDLE_EVENT_LOG",
    "SCM_IMPORT_AW(RegisterEventSource);",
    "SBIEDLL_HOOK_SCM(RegisterEventSourceA);",
    "SBIEDLL_HOOK_SCM(RegisterEventSourceW);",
    "SCM_IMPORT___(DeregisterEventSource);",
    "SBIEDLL_HOOK_SCM(DeregisterEventSource);",
    "SCM_IMPORT_AW(ReportEvent);",
    "SBIEDLL_HOOK_SCM(ReportEventA);",
    "SBIEDLL_HOOK_SCM(ReportEventW);",
    "SCM_IMPORT___(CloseEventLog);",
    "SBIEDLL_HOOK_SCM(CloseEventLog);",
]:
    require(scm_c, term, "scm.c hook topology")

for term in [
    "RegisterEventSourceA",
    "ReportEventA",
    "DeregisterEventSource",
    "RtlAnsiStringToUnicodeString",
    "HANDLE_EVENT_LOG",
    "ERROR_INVALID_HANDLE",
    "CloseEventLog",
]:
    require(spec, term, "spec shape")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-187",
    "owner: Sandboxie/core/dll/scm_event.c",
    "spec: docs/plan/srev-187-scm-event-log-fake-handle-contract.md",
    "schema: docs/plan/srev-187-scm-event-log-fake-handle-contract.schema.json",
    "checker: docs/plan/check-srev-187.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-187: SCM Event Log Fake Handle Contract",
    "SCM_EVENT_LOG_FAKE_HANDLE_CONTRACT",
    "Sandboxie/core/dll/scm_event.c",
    "Scm_RegisterEventSourceA",
    "Scm_ReportEventW",
    "Scm_DeregisterEventSource",
]:
    require(ledger, term, "combined ledger")

print("SREV-187 schema/source gate passed")
