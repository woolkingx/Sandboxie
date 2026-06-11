---
kind: srev-ledger-entry
id: SREV-014
title: FSCTL_PIPE_WAIT Parser Reads NameLength Before Input Buffer Shape Check
status: patched-source-level-after-official-fscc-waitnamedpipe-shape-analysis-needs-wind
owner: "Sandboxie/core/dll/file_pipe.c:1314"
spec: docs/plan/srev-014-fsctl-pipe-wait-spec.md
schema: docs/plan/srev-014-fsctl-pipe-wait-spec.schema.json
checker: docs/plan/check-srev-014.sh
runtime_gate: "malformed short buffers pass to native validation without hook-side reads; valid `WaitNamedPipeW` still rewrites sandbox pipe names"
---
### SREV-014: FSCTL_PIPE_WAIT Parser Reads NameLength Before Input Buffer Shape Check

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official FSCC/WaitNamedPipe shape analysis; needs Windows runtime proof |
| Evidence | Explorer Ohm reports `Sandboxie/core/dll/file_pipe.c:1314` reads `FILE_PIPE_WAIT_FOR_BUFFER.NameLength` and copies `Name` before checking `InputBufferLength`. |
| Data | Caller-provided FSCTL input buffer for `FSCTL_PIPE_WAIT`. |
| Schema | Buffer must contain fixed header first; `NameLength` must be even and fit within `InputBufferLength - FIELD_OFFSET(..., Name)`. |
| Topology | Sandboxed caller buffer crosses into pipe-name rewrite hook. |
| Logic Risk | Malformed short buffer can crash or leak adjacent memory into rewritten pipe-name path. |
| Official Shape | `docs/plan/srev-014-fsctl-pipe-wait-spec.md` records MS-FSCC `FSCTL_PIPE_WAIT` request/reply, SMB2 handling posture, and Win32 `WaitNamedPipe` surface semantics. |
| Fix | `File_WaitNamedPipe` now proves the fixed FSCTL buffer header exists before reading `NameLength`, requires WCHAR-aligned `NameLength`, proves the name bytes fit inside `InputBufferLength`, and checks rewritten-buffer allocation before writing. |
| Acceptance Gate | `docs/plan/check-srev-014.sh` proves the fixed-header gate precedes `NameLength` use and that name range/allocation checks exist. Windows gate: malformed short buffers pass to native validation without hook-side reads; valid `WaitNamedPipeW` still rewrites sandbox pipe names. |
