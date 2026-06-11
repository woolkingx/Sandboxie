#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-092/322 capture failed: {label} missing {needle!r}")


playbook = (ROOT / "docs/plan/srev-092-322-user-lifecycle-runtime-capture-playbook.md").read_text()
schema = json.loads(
    (ROOT / "docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json").read_text()
)
srev092 = (ROOT / "docs/plan/srev-092-scm-msi-loader-unload-event-owner.md").read_text()
srev322 = (ROOT / "docs/plan/srev-322-proc-werfault-dump-suppression-boundary.md").read_text()
check092 = (ROOT / "docs/plan/check-srev-092.py").read_text()
check322 = (ROOT / "docs/plan/check-srev-322.py").read_text()

if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-092/322 capture failed: schema is not draft-07")
if schema.get("id") != "USER_LIFECYCLE_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-092/322 capture failed: wrong schema id")

for term in [
    "official lifecycle/API shape -> Windows runtime capture -> local lifecycle owner decision",
    "one handle closed or one dump exists -> last-owner and caller-visible semantics are proven",
    "feature path: `msi-last-user-event`",
    "feature path: `werfault-localdumps-boundary`",
    "MsiCloseHandle(one handle) -x-> proven last MSI user",
    "dump file exists -x-> duplicate suppression and PROCESS_INFORMATION semantics proven",
]:
    require(playbook, term, "playbook")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/msi/nf-msi-msiclosehandle",
    "https://learn.microsoft.com/en-us/windows/win32/sync/event-objects",
    "https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps",
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess",
]:
    require(playbook, term, "playbook official reference")

schema_text = json.dumps(schema, sort_keys=True)
for term in [
    "record_id",
    "windows_build",
    "architecture",
    "sandboxie_commit",
    "feature_path",
    "msi-last-user-event",
    "werfault-localdumps-boundary",
    "route_result",
    "msi-event-held",
    "msi-server-kept-alive",
    "werfault-first-resumed",
    "werfault-duplicate-terminated",
    "module_lifecycle",
    "msi_dll_load_notification",
    "scm_msidll_call_count",
    "event_lifecycle",
    "create_event_result",
    "msiserver_open_event_failure",
    "msi_handle_lifecycle",
    "msi_close_handle",
    "cross_thread_handle_owner",
    "msi_close_all_handles_diagnostic_count",
    "msiserver_lifecycle",
    "non_exit_while_custom_action_active",
    "wer_configuration",
    "global_localdumps",
    "dump_count",
    "automatic_debugger_configured",
    "sandbox_configuration",
    "enable_minidump",
    "werfault_path",
    "duplicate_process_ids",
    "sbie_log_2224",
    "dump_output",
    "dumpcount_replacement_observed",
    "handle_semantics",
    "get_exit_code_process_result",
    "wait_for_single_object_result",
]:
    require(schema_text, term, "schema")

for term in [
    "Shared Runtime Capture Evidence",
    "srev-092-322-user-lifecycle-runtime-capture.schema.json",
    "srev-092-322-user-lifecycle-runtime-capture-playbook.md",
    "msi-last-user-event",
    "Windows gate: validate captured MSI lifecycle records",
]:
    require(srev092, term, "SREV-092 adjacency")
    require(check092, term, "SREV-092 checker adjacency")

for term in [
    "Shared Runtime Capture Evidence",
    "srev-092-322-user-lifecycle-runtime-capture.schema.json",
    "srev-092-322-user-lifecycle-runtime-capture-playbook.md",
    "werfault-localdumps-boundary",
    "Windows gate: validate captured WerFault lifecycle records",
]:
    require(srev322, term, "SREV-322 adjacency")
    require(check322, term, "SREV-322 checker adjacency")

print("SREV-092/322 user lifecycle runtime capture gate passed")
