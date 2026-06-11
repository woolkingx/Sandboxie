---
kind: srev-ledger-entry
id: SREV-331
title: File Filter Spooler Probe Exceptions
status: patched-comment-topology-after-official-spooler-port-monitor-review-no-behavior-change
owner: Sandboxie/core/drv/file_flt.c
spec: docs/plan/srev-331-file-flt-spooler-probe-exceptions.md
schema: docs/plan/srev-331-file-flt-spooler-probe-exceptions.schema.json
checker: docs/plan/check-srev-331.py
runtime_gate: Windows print matrix for spooler probe exceptions and print-to-file denial
---

### SREV-331: File Filter Spooler Probe Exceptions

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official spooler and port-monitor review; no behavior change |
| Evidence | `file_flt.c` blocks generic-write create requests from system-account `spoolsv.exe` while it impersonates a sandboxed user, unless `AllowSpoolerPrintToFile` is enabled or the target is in the spooler work directory. The branch already excludes target names ending in `:`, `tpwinprn-stat.txt`, and `\pipe\spoolss`, but two comments described those exceptions as arbitrary hacks. |
| Data | `IRP_MJ_CREATE`, `SBIE_FILE_GENERIC_WRITE`, `spoolsv.exe`, `MyIsProcessRunningAsSystemAccount`, `GetThreadTokenOwnerPid`, `Process_Find`, `ipc_allowSpoolerPrintToFile`, `spooler_directory`, `UnicodeStringEndsWith(..., L":", TRUE)`, `tpwinprn-stat.txt`, `\pipe\spoolss`, and `File_CreateOperation`. |
| Schema | `FILE_FLT_SPOOLER_PROBE_EXCEPTIONS` says `file_flt.c` owns the spoolsv impersonated write deny gate; spooler probe exceptions remain scoped to spoolsv generic-write create requests from a system-account process impersonating a sandboxed user; target names ending in `:` fall through so native path or device-name parsing owns the failure status; `tpwinprn-stat.txt` remains a printer-driver status probe exception; `\pipe\spoolss` remains a spooler pipe exception; `AllowSpoolerPrintToFile` and `spooler_directory` behavior remain unchanged; this SREV changes comments and proof only. |
| Topology | `spoolsv.exe + SBIE_FILE_GENERIC_WRITE + system account -> sandbox owner process -> print-to-file deny gate -> narrow probe exceptions -> native filesystem/device/pipe owner decides result`. Non-exception spooler write creates still route to `File_CreateOperation` or `STATUS_ACCESS_DENIED`. |
| Logic Risk | The stale comments made the exceptions look broad and arbitrary. In a security boundary, that can lead future edits to expand the exceptions outside the spooler gate, apply them to non-spooler processes, or replace native path/device-name failure with sandbox denial. |
| Official Shape | Microsoft documents the print spooler as accepting print data, spooling data to files, and communicating with printer hardware. Microsoft documents `Spoolsv.exe` as the spooler API server and port monitors as user-mode components that commonly use `CreateFile`, `WriteFile`, `ReadFile`, and `DeviceIoControl` to communicate with port drivers. Microsoft documents `:` as reserved in ordinary file and directory names, while `CreateFile` can also open files, streams, devices, mailslots, and pipes; communications resources such as COM/LPT ports are `CreateFile` targets. |
| Fix | Comment-only source clarification. The source now names SREV-331 and describes the `:` suffix and `tpwinprn-stat.txt` branches as scoped spooler/port-monitor probe exceptions. No predicate, access mask, process-name check, sandbox-owner check, pipe exception, file policy call, or return status changed. |
| Acceptance Gate | `docs/plan/check-srev-331.py` validates the draft-07 schema, official references, `spoolsv.exe` / `SBIE_FILE_GENERIC_WRITE` / system-account / sandbox-owner gates, the three existing exceptions, source comment ownership, stale hack wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-331.sh` is the targeted wrapper. Runtime gate: Windows print matrix with a sandboxed print-to-file denial, allowed spooler work directory, `AllowSpoolerPrintToFile=y`, a printer/port driver path ending in `:`, `tpwinprn-stat.txt`, `\pipe\spoolss`, and a negative control proving non-spooler write creates do not inherit these exceptions. |
