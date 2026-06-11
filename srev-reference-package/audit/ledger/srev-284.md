---
kind: srev-ledger-entry
id: SREV-284
title: Device-Control Bootstrap Recursion Guard
status: patched-comment-topology-after-official-device-control-bootstrap-review-no-behavior-change
owner: Sandboxie/core/dll/file_pipe.c
spec: docs/plan/srev-284-device-control-bootstrap-recursion-guard.md
schema: docs/plan/srev-284-device-control-bootstrap-recursion-guard.schema.json
checker: docs/plan/check-srev-284.py
runtime_gate: Windows hook-bootstrap trace plus normal post-install NtDeviceIoControlFile pass-through and SREV-281 TCP/NSI deny behavior
---

### SREV-284: Device-Control Bootstrap Recursion Guard

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official device-control bootstrap review; no behavior change |
| Evidence | `File_NtDeviceIoControlFile` checks `if (!__sys_NtDeviceIoControlFile) return STATUS_BAD_INITIAL_PC;` before native pass-through. `SbieApi_Ioctl` uses `__sys_NtDeviceIoControlFile` to bypass the hook after that native pointer is published, but falls back to `NtDeviceIoControlFile` before publication. The old comment described the recursion/logging symptom but did not name the bootstrap owner boundary. |
| Data | `File_NtDeviceIoControlFile`, `__sys_NtDeviceIoControlFile`, `STATUS_BAD_INITIAL_PC`, `SbieApi_Ioctl`, `SbieApi_MonitorPutMsg`, `API_SBIEDRV_CTLCODE`, `NtDeviceIoControlFile`, `IoControlCode`, SREV-281, and SREV-139. |
| Schema | `DEVICE_CONTROL_BOOTSTRAP_RECURSION_GUARD` says `NtDeviceIoControlFile` sends IOCTL codes to a target device driver; `IoControlCode` selects the operation and buffer shape; `File_NtDeviceIoControlFile` owns the bootstrap guard before native pointer publication; `__sys_NtDeviceIoControlFile` is the native pass-through owner after hook installation; `SbieApi_Ioctl` bypasses the hook through `__sys_NtDeviceIoControlFile` once that pointer is available; before native pointer publication the guard returns `STATUS_BAD_INITIAL_PC` as a local sentinel; SREV-281 owns the `BlockNetParam` TCP/NSI policy; SREV-139 owns driver-side DeviceIoControl deny completion; this SREV changes comments and proof only. |
| Topology | Normal installed state: `File_NtDeviceIoControlFile -> __sys_NtDeviceIoControlFile`. SbieApi after native pointer publication: `SbieApi_Ioctl -> __sys_NtDeviceIoControlFile`. Bootstrap pre-publication state: `monitor/API path -> SbieApi_Ioctl -> NtDeviceIoControlFile export -> File_NtDeviceIoControlFile -> STATUS_BAD_INITIAL_PC sentinel`. |
| Logic Risk | Without the owner boundary, the guard can look like disposable log-noise handling. Removing it or replacing it with native pass-through before the native pointer exists can mix bootstrap state with regular device-control policy. The sentinel is narrow and must not be treated as TCP/NSI denial or driver-side completion behavior. |
| Official Shape | Microsoft documents `ZwDeviceIoControlFile` / user-mode `NtDeviceIoControlFile` as sending IOCTL codes to device drivers, and documents IOCTLs as the operation-selection shape for device-control calls. |
| Fix | Comment-only source clarification. The source now names SREV-284 and states that the guard applies only while `__sys_NtDeviceIoControlFile` is unpublished, so Sandboxie's own monitor/API path does not re-enter the partially installed hook. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-284.py` validates the draft-07 schema, official references, source guard predicate and sentinel, native pass-through preservation, SbieApi bypass adjacency, SREV-281/SREV-139 adjacency, stale source wording removal, and ledger fragment; `docs/plan/check-srev-284.sh` is the targeted wrapper. Runtime gate: Windows hook-bootstrap trace proving monitor/API traffic before native pointer publication observes the sentinel without recursive hook entry, plus normal post-install `NtDeviceIoControlFile` pass-through and SREV-281 TCP/NSI deny behavior. |
