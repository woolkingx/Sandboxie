---
kind: srev-ledger-entry
id: SREV-338
title: Session Monitor Object Name Staging
status: patched-comment-topology-after-official-object-name-unicode-monitor-staging-review-no-behavior-change
owner: Sandboxie/core/drv/session.c
spec: docs/plan/srev-338-session-monitor-object-name-staging.md
schema: docs/plan/srev-338-session-monitor-object-name-staging.schema.json
checker: docs/plan/check-srev-338.py
runtime_gate: Windows monitor trace matrix for long monitor names object names truncation and IPC/pipe checks
---

### SREV-338: Session Monitor Object Name Staging

| Field | Content |
|---|---|
| Severity | [low] |
| Status | patched comment/topology after official object-name, Unicode string, and monitor staging review; no behavior change |
| Evidence | `Session_Api_MonitorPut2` converts `args->log_len` from bytes to WCHAR count, caps the local staged name at `max_buff = 2048`, allocates `(max_buff + 4) * sizeof(WCHAR)`, copies user monitor data into `name`, writes a local terminator, optionally probes IPC or pipe object existence, copies `Obj_GetNameOrFileName` counted `Name->Name.Length` into the same buffer, writes another local terminator, and passes `name` to `Session_MonitorPutEx` with `lengths == NULL`. The old source had a TODO asking whether to increase the allocation and a stale `1028` buffer-size comment. |
| Data | `Session_Api_MonitorPut2`, `API_MONITOR_PUT2_ARGS.log_len`, `log_data`, `max_buff`, `name`, `Mem_Alloc`, `wmemcpy`, `Obj_ObjectTypes`, `ObReferenceObjectByName`, `IoCreateFileSpecifyDeviceObjectHint`, `ObReferenceObjectByHandle`, `Obj_GetNameOrFileName`, `OBJECT_NAME_INFORMATION.Name`, `UNICODE_STRING.Length`, `Session_MonitorPutEx`, `wcslen`, and `log_buffer_push_bytes`. |
| Schema | `SESSION_MONITOR_OBJECT_NAME_STAGING` says `Session_Api_MonitorPut2` owns conversion from user byte length or counted object-manager name to a bounded local WCHAR staging string; `max_buff` is a WCHAR count and not a byte count; the staging allocation keeps plus four WCHARs of slack so truncation can still write a local NUL terminator; `Obj_GetNameOrFileName` returns `OBJECT_NAME_INFORMATION.Name` as a counted `UNICODE_STRING`; `Name.Length` is a byte count and is converted to WCHAR count before copy; `Session_MonitorPutEx` uses `wcslen` when `lengths` is `NULL`, so the staged name must be NUL-terminated; this SREV changes comments and proof only. |
| Topology | `user monitor input { byte length, user pointer } -> ProbeForRead -> WCHAR-counted local staging buffer -> optional object-existence probe -> counted object-manager name -> local NUL-terminated monitor string -> Session_MonitorPutEx with lengths == NULL`. Object route: `Obj_ObjectTypes / ObReferenceObjectByName` for IPC and `IoCreateFileSpecifyDeviceObjectHint / ObReferenceObjectByHandle` for pipes, then `Obj_GetNameOrFileName -> Name->Name.Length / sizeof(WCHAR) -> local staged name`. |
| Logic Risk | The old TODO suggested that a larger buffer was the important decision. The real invariant is that byte-counted and object-manager-counted strings must be converted into a bounded NUL-terminated local string before the monitor writer uses `wcslen`. Future edits that treat `max_buff` as bytes, remove the terminator, or pass counted object names with `lengths == NULL` could let monitor logging scan beyond the intended extent. |
| Official Shape | Microsoft documents `ObQueryNameString` as returning `OBJECT_NAME_INFORMATION.Name`, a `UNICODE_STRING`; `UNICODE_STRING.Length` is a byte count that excludes a trailing NUL when present; and `IoCreateFileSpecifyDeviceObjectHint` uses initialized `OBJECT_ATTRIBUTES` with a buffered Unicode object name and `OBJ_KERNEL_HANDLE` outside system process context. |
| Fix | Comment-only source clarification. The source now names SREV-338, states that `name` is a WCHAR-counted monitor staging buffer, and explains that the `+4` allocation slack preserves NUL termination after truncation. The stale `1028`/TODO wording is removed. No cap, allocation size, object probe, object name query, copy length, terminator write, monitor ring format, or runtime behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-338.py` validates the draft-07 schema, official references, `Session_Api_MonitorPut2` user string staging, `max_buff` cap, `(max_buff + 4) * sizeof(WCHAR)` allocation, explicit NUL termination after both user and object-name copies, counted `Name->Name.Length` use, monitor writer `wcslen` adjacency, stale TODO removal, SREV-028 / SREV-155 / SREV-160 / SREV-171 / SREV-232 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-338.sh` is the targeted wrapper. Runtime gate: Windows monitor trace matrix with long user monitor strings, long object-manager names, exact `max_buff` length, truncation, IPC object existence checks, pipe object checks, unnamed objects, and stack-trace-enabled monitor entries. |
