---
kind: srev-ledger-entry
id: SREV-187
title: SCM Event Log Fake Handle Contract
status: patched-source-level-after-official-event-log-and-rtl-string-review-needs-windows-dll-runtime-proof
owner: Sandboxie/core/dll/scm_event.c
spec: docs/plan/srev-187-scm-event-log-fake-handle-contract.md
schema: docs/plan/srev-187-scm-event-log-fake-handle-contract.schema.json
checker: docs/plan/check-srev-187.py
runtime_gate: Windows DLL build for advapi32 event-log hooks, fake-handle ReportEvent/DeregisterEventSource smoke, invalid-handle ERROR_INVALID_HANDLE smoke, and CloseEventLog native-close regression smoke
---
### SREV-187: SCM Event Log Fake Handle Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official Event Log and RTL string conversion review; needs Windows DLL runtime proof |
| Evidence | `Sandboxie/core/dll/scm_event.c` was the highest-ranked unnamed reviewable core file after SREV-186. It hooks `RegisterEventSourceA/W`, `ReportEventA/W`, `DeregisterEventSource`, and `CloseEventLog`. The W register path returns the Sandboxie fake `HANDLE_EVENT_LOG` and suppresses host event-log writes. Before this SREV, the A register path ignored `RtlAnsiStringToUnicodeString` status before using `uni.Buffer`; `DeregisterEventSource` and `ReportEventA/W` returned success for every handle value rather than only the local fake handle. |
| Data | `Sandboxie/core/dll/scm_event.c`, `Sandboxie/core/dll/scm.c`, `HANDLE_EVENT_LOG`, `Scm_RegisterEventSourceW`, `Scm_RegisterEventSourceA`, `Scm_DeregisterEventSource`, `Scm_ReportEventW`, `Scm_ReportEventA`, `Scm_CloseEventLog`, `RtlAnsiStringToUnicodeString`, `RtlFreeUnicodeString`, `P_RegisterEventSource`, `P_DeregisterEventSource`, `P_ReportEvent`, and `P_CloseEventLog`. |
| Schema | `SCM_EVENT_LOG_FAKE_HANDLE_CONTRACT` says `scm_event.c` owns DLL-side event-log write suppression; `RegisterEventSourceW` returns only the Sandboxie fake event-log handle and does not open a host writer; `RegisterEventSourceA` checks `RtlAnsiStringToUnicodeString` before passing the converted source name to the W path; `ReportEventA/W` and `DeregisterEventSource` consume handles returned by `RegisterEventSource`, and only `HANDLE_EVENT_LOG` is a valid local handle; invalid or non-local event-source handles fail with `ERROR_INVALID_HANDLE`; `CloseEventLog` remains separate and passes non-local event-log handles to native close; `ReportEventA/W` local prototypes keep the official pointer-to-string-array shape; host event-log brokering, service-control APIs, and read-side event-log handles do not change. |
| Topology | Legal local write-suppression flow is `RegisterEventSourceA/W` -> local fake `HANDLE_EVENT_LOG` -> `ReportEventA/W` suppresses host write only for `HANDLE_EVENT_LOG` -> `DeregisterEventSource` closes only `HANDLE_EVENT_LOG`. Separate read/close flow is native event-log handle -> `CloseEventLog` -> `__sys_CloseEventLog`. |
| Logic Risk | The old A path used an unproven Unicode output after a conversion/allocation API that returns `NTSTATUS`. The old report/deregister paths also reported success for invalid or non-local handles, which made the local fake-handle policy broader than its owner and hid caller bugs. Returning success for arbitrary handles is not required to suppress host writes; fake-handle success plus invalid-handle failure preserves isolation with a clearer API contract. |
| Official Shape | `docs/plan/srev-187-scm-event-log-fake-handle-contract.md` records Microsoft `RegisterEventSourceA`, `ReportEventA`, `DeregisterEventSource`, and `RtlAnsiStringToUnicodeString` references. `docs/plan/srev-187-scm-event-log-fake-handle-contract.schema.json` records the JSON Schema draft-07 local `SCM_EVENT_LOG_FAKE_HANDLE_CONTRACT` contract. |
| Fix | `Scm_RegisterEventSourceA` now initializes `uni.Buffer`, checks `RtlAnsiStringToUnicodeString`, maps conversion failure to a Win32 last-error, and frees only a proven allocated buffer. `Scm_DeregisterEventSource`, `Scm_ReportEventW`, and `Scm_ReportEventA` now return success only for `HANDLE_EVENT_LOG`; other handles fail with `ERROR_INVALID_HANDLE`. `ReportEventA/W` prototypes now use pointer-to-string-array parameters. |
| Acceptance Gate | `docs/plan/check-srev-187.py` validates the draft-07 schema, official references, fake-handle event-log topology, ANSI conversion status gate, fake-only `ReportEventA/W` and `DeregisterEventSource` success, `CloseEventLog` native close preservation, hook import topology, and ledger fragment; `docs/plan/check-srev-187.sh` is the matrix wrapper. Runtime gate: Windows DLL build for `advapi32.dll` event-log hooks, sandboxed fake-handle report/deregister smoke with no host event-log write, invalid/non-local handle `ERROR_INVALID_HANDLE` smoke, and native `CloseEventLog` close regression smoke. |
