---
kind: srev-ledger-entry
id: SREV-200
title: FileServer OpenBoxFile Path Gate
status: patched-source-level-after-official-ntcreatefile-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/fileserver.h
implementation: Sandboxie/core/svc/fileserver.cpp
spec: docs/plan/srev-200-file-server-openboxfile-path-gate.md
schema: docs/plan/srev-200-file-server-openboxfile-path-gate.schema.json
checker: docs/plan/check-srev-200.py
runtime_gate: Windows service build plus outside-sandbox SetAttributes and SetShortName denial smoke
---

### SREV-200: FileServer OpenBoxFile Path Gate

| Field | Content |
|---|---|
| Severity | [critical] |
| Status | patched source-level after official NtCreateFile shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/fileserver.h` was the top unnamed reviewable core file after SREV-199. Its implementation in `Sandboxie/core/svc/fileserver.cpp` has `FileServer::OpenBoxFile`, which calls `CheckBoxFilePath` before privileged `NtCreateFile`. Before this fix, the failure branch executed `SHORT_REPLY(status);` inside an `NTSTATUS` helper without returning, so an outside-sandbox or otherwise denied path could still proceed to `RtlInitUnicodeString`, `InitializeObjectAttributes`, and `NtCreateFile` in the service process. |
| Data | `FILE_SET_ATTRIBUTES_REQ`, `FILE_SET_SHORT_NAME_REQ`, counted WCHAR wire paths, `FileServer::OpenBoxFile`, `CheckBoxFilePath`, `SbieApi_QueryProcessPath`, `RtlInitUnicodeString`, `InitializeObjectAttributes`, `NtCreateFile`, `desired_access`, and `create_options`. |
| Schema | `FILE_SERVER_OPENBOXFILE_PATH_GATE` says the wire path must be validated before `OpenBoxFile`, `CheckBoxFilePath` failure is terminal, `NtCreateFile` is reachable only after sandbox path-gate success, and only `MSG_HEADER *` handlers may use `SHORT_REPLY`. |
| Topology | Legal flow is `sandboxed wire request -> SetAttributes/SetShortName handler -> bounded path validation -> OpenBoxFile -> CheckBoxFilePath -> NtCreateFile only on success -> handler SHORT_REPLY(status)`. |
| Logic Risk | The old helper confused reply construction with helper status return. Because `NtCreateFile` opens the object named by `OBJECT_ATTRIBUTES` with requested access, continuing after a failed sandbox-root check could let a service broker path operation reach a caller-supplied host path. |
| Official Shape | `docs/plan/srev-200-file-server-openboxfile-path-gate.md` records Microsoft `NtCreateFile`, `InitializeObjectAttributes`, and `RtlInitUnicodeString` references. `docs/plan/srev-200-file-server-openboxfile-path-gate.schema.json` records the JSON Schema draft-07 local `FILE_SERVER_OPENBOXFILE_PATH_GATE` contract. |
| Fix | `OpenBoxFile` now returns `status` immediately when `CheckBoxFilePath` fails. `SetAttributes` and `SetShortName` still own reply construction and convert the helper's `NTSTATUS` to `SHORT_REPLY(status)` at the handler boundary. No desired-access, share-mode, create-options, or wire string validation behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-200.py` validates the draft-07 schema, official references, header/implementation owner coordinates, `OpenBoxFile` path-gate ordering, stale `SHORT_REPLY(status);` removal from the `NTSTATUS` helper, preserved handler boundary replies, and split ledger fragment; `docs/plan/check-srev-200.sh` is the targeted wrapper. Runtime/build gate: Windows service build plus outside-sandbox `MSGID_FILE_SET_ATTRIBUTES` and `MSGID_FILE_SET_SHORT_NAME` denial smoke. |
