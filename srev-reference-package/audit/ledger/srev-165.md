---
kind: srev-ledger-entry
id: SREV-165
title: Process Wire String Bounds
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/svc/ProcessServer.cpp
spec: docs/plan/srev-165-process-wire-string-bounds.md
schema: docs/plan/srev-165-process-wire-string-bounds.schema.json
checker: docs/plan/check-srev-165.py
runtime_gate: "Windows service build, sandboxed process launch, updater launch by signed caller, malformed IPC packet smoke, and forced allocation failure smoke"
---

### SREV-165: Process Wire String Bounds

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after process broker wire-string and Microsoft process/heap API review; needs Windows service runtime proof |
| Evidence | `Sandboxie/core/svc/ProcessServer.h` was the top unnamed reviewable core file after SREV-164. It declares `RunSandboxedCopyString`, `RunSandboxedHandler`, and `RunUpdaterHandler`. `Sandboxie/core/svc/ProcessWire.h` defines process launch wire fields as offsets plus `ULONG` string lengths. Before this SREV, `Sandboxie/core/svc/ProcessServer.cpp` multiplied caller-provided lengths by `sizeof(WCHAR)` inside validation expressions and `RunUpdaterHandler` wrote to `cmd` without checking whether `HeapAlloc` returned `NULL`. |
| Data | `Sandboxie/core/svc/ProcessServer.h`, `Sandboxie/core/svc/ProcessServer.cpp`, `Sandboxie/core/svc/ProcessWire.h`, `PROCESS_RUN_SANDBOXED_REQ`, `PROCESS_RUN_UPDATER_REQ`, `RunSandboxedCopyString`, `RunSandboxedHandler`, `RunUpdaterHandler`, `MSG_HEADER.length`, `cmd_ofs`, `cmd_len`, `dir_ofs`, `dir_len`, `env_ofs`, `env_len`, `PIPE_MAX_DATA_LEN`, `HeapAlloc`, and `CreateProcessAsUser`. |
| Schema | `PROCESS_WIRE_STRING_BOUNDS` says `ProcessServer.cpp` owns service-side validation for process broker wire strings; `ProcessWire.h` lengths are WCHAR counts, not byte counts; a WCHAR count must be checked against `PIPE_MAX_DATA_LEN / sizeof(WCHAR)` before multiplying by `sizeof(WCHAR)`; offset validation must prove `ofs <= msg->length` before computing available bytes; validation must compare byte length against available bytes and must not depend on `ofs + byte_len`; and `RunUpdaterHandler` must check `HeapAlloc` before writing to `cmd`. |
| Topology | Legal flow is `PROCESS_RUN_SANDBOXED_REQ` / `PROCESS_RUN_UPDATER_REQ` -> `MSG_HEADER.length` -> offset plus WCHAR count -> count cap before byte conversion -> available bytes from message length -> broker-owned mutable WCHAR buffer -> `CreateProcessAsUserW`. |
| Logic Risk | Multiplying an untrusted `ULONG` count before proving it fits can wrap the byte count used by validation and copying. That can turn an invalid wire shape into a truncated broker string or make updater allocation/copy logic operate on a shape that was never valid. Separately, dereferencing the updater command allocation without a `NULL` check can crash the service under allocation failure. |
| Official Shape | `docs/plan/srev-165-process-wire-string-bounds.md` records Microsoft `CreateProcessAsUserW`, `HeapAlloc`, and environment-block references. `docs/plan/srev-165-process-wire-string-bounds.schema.json` records the JSON Schema draft-07 local `PROCESS_WIRE_STRING_BOUNDS` contract. |
| Fix | `RunSandboxedCopyString` now rejects counts above `PIPE_MAX_DATA_LEN / sizeof(WCHAR)`, computes `bytes` only after that cap, proves `ofs <= msg->length`, computes `available = msg->length - ofs`, and compares the byte length against `available`. `RunUpdaterHandler` now uses the same pre-multiply count cap, computes `cmd_bytes`, validates against `available`, uses `cmd_bytes` for `memcpy`, and returns `ERROR_NOT_ENOUGH_MEMORY` when command-buffer allocation fails. Process-token ownership, DACL policy, startup flag filtering, handle filtering, and `CreateProcessAsUser` call topology are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-165.py` validates the draft-07 schema, official references, header/wire declarations, service-side count-before-byte validation, available-byte topology, removal of raw `ofs + byte_len` validation, updater allocation failure handling, ledger entry, and source rejection of stale multiplication patterns; `docs/plan/check-srev-165.sh` is the matrix wrapper. Runtime/build gate: Windows service build; normal sandboxed process launch; updater launch by signed caller; malformed service IPC packets with oversized WCHAR counts, offset past message length, short payload, empty string, and large valid payload; low-memory or forced-allocation-failure smoke for updater command buffer. |
