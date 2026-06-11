---
kind: srev-ledger-entry
id: SREV-299
title: IPC CreateObjects Bootstrap Allocation Gate
status: patched-source-level-local-bootstrap-allocation-gate-needs-windows-runtime-proof
owner: Sandboxie/core/dll/ipc.c
spec: docs/plan/srev-299-ipc-createobjects-bootstrap-allocation-gate.md
schema: docs/plan/srev-299-ipc-createobjects-bootstrap-allocation-gate.schema.json
checker: docs/plan/check-srev-299.py
runtime_gate: Windows IPC namespace bootstrap, Ipc_GetName failure, and allocation-failure injection; symbolic-link reparse design remains open
---

### SREV-299: IPC CreateObjects Bootstrap Allocation Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level local bootstrap allocation gate; needs Windows runtime proof |
| Evidence | `Ipc_CreateObjects` creates a dummy event under the sandboxed `BaseNamedObjects` namespace, queries it through `Ipc_GetName`, trims the dummy leaf from `CopyPath`, and then creates `BNOLINKS`, `Global`, `Local`, and `Session` object-directory/symbolic-link topology through `SbieApi_CreateDirOrLink`. The old comment admitted that symbolic-link reparse was not the current design. Around that comment, `buffer`, `BNOLINKS`, `buffer2`, and `GLOBAL` were allocated and immediately written through without null gates. If `Ipc_GetName` failed after `CreateEvent` succeeded, the dummy event handle also skipped the normal `NtClose(handle)` path. Windows runtime capture later proved `BNOLINKS` was being built as a sibling of the session IPC root, causing the initial SREV-037 driver boxed-path gate to reject the bootstrap directory with `STATUS_ACCESS_DENIED`; moving `BNOLINKS` under `Dll_BoxIpcPath` removed that denial but made `Start.exe` hit the name-buffer depth guard before launching targets. |
| Data | `Ipc_CreateObjects`, dummy `CreateEvent`, `Ipc_GetName`, `TruePath`, `CopyPath`, `buffer`, `BNOLINKS`, `GLOBAL`, `buffer2`, `SbieApi_CreateDirOrLink`, `BaseNamedObjects`, `Global`, `Local`, `Session`, and SREV-037. |
| Schema | `IPC_CREATEOBJECTS_BOOTSTRAP_ALLOCATION_GATE` says `Ipc_CreateObjects` owns local bootstrap storage and dummy event handle cleanup; `buffer`, `BNOLINKS`, `buffer2`, and `GLOBAL` must be allocation-proven before string writes; the dummy event handle must be closed on normal and failure exits; `SbieApi_CreateDirOrLink` owns the driver-side directory or symbolic-link creation request; SREV-037 must accept the box-level `BNOLINKS` bootstrap auxiliary path without broadening normal IPC path creation; the broader symbolic-link reparse design remains a separate runtime design gate. |
| Topology | `CreateEvent dummy object -> Ipc_GetName -> CopyPath -> SbieApi_CreateDirOrLink main directory`; `CopyPath -> box-level BNOLINKS -> BaseNamedObjects / Global / Local / Session object-link topology`; SREV-037 owns the driver-side counted-string and boxed-path gate. |
| Logic Risk | The earlier code could write through null bootstrap buffers before reaching the driver-side boxed-path gate. It could also leave the dummy event handle open on the `Ipc_GetName` failure path. The stale `todo/fix-me` comment mixed a future symbolic-link reparse design with the local allocation/handle owner. |
| Official Shape | Microsoft documents object directories as object-manager containers, `CreateEventW` as creating or opening a named event and returning a handle, kernel objects as handle-owned objects, `NtQueryObject` as object-information query by handle, and symbolic-link creation as a link-name/target-name boundary. SREV-037 records the local driver API shape for `SbieApi_CreateDirOrLink`. |
| Fix | `Ipc_CreateObjects` now initializes the dummy event handle to `NULL`, clears it after normal `NtClose`, and closes it in `finish` if an earlier exit still owns it. The function now gates `buffer`, `BNOLINKS`, `buffer2`, and `GLOBAL` allocations with `STATUS_INSUFFICIENT_RESOURCES` before any string write. `BNOLINKS` remains a box-level bootstrap auxiliary directory; SREV-037 owns the narrow driver-side exception that permits only this same-box auxiliary subtree in addition to the configured IPC root. The stale source comment was replaced with an SREV-299 topology comment that leaves full symbolic-link reparse as a separate design gate. |
| Acceptance Gate | `docs/plan/check-srev-299.py` validates the draft-07 schema, official references, source allocation gates before first writes, dummy event handle cleanup, SREV-037 adjacency, stale comment removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-299.sh` is the targeted wrapper. Runtime gate: Windows IPC namespace bootstrap under normal startup, forced `Ipc_GetName` failure, and allocation-failure injection for each bootstrap buffer. The broader symbolic-link reparse design remains open. |
