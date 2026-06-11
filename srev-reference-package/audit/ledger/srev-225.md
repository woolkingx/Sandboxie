---
kind: srev-ledger-entry
id: SREV-225
title: Interactive File Migration Path Bounds
status: patched-source-level-after-local-interactive-wire-request-contract-review-needs-windows-ui-runtime-proof
owner: Sandboxie/core/svc/InteractiveWire.h
spec: docs/plan/srev-225-interactive-file-migration-path-bounds.md
schema: docs/plan/srev-225-interactive-file-migration-path-bounds.schema.json
checker: docs/plan/check-srev-225.py
runtime_gate: "Windows DLL and SandboxiePlus build plus normal and over-255-character file migration prompt smokes"
---
### SREV-225: Interactive File Migration Path Bounds

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after local interactive wire request contract review; needs Windows UI runtime proof |
| Evidence | `Sandboxie/core/svc/InteractiveWire.h` was the top unnamed reviewable core file after SREV-224. It defines `MAN_FILE_MIGRATION_REQ.file_path[256]`. The DLL-side producer in `Sandboxie/core/dll/file_copy.c` copied `TruePath` into that fixed field with `wcscpy(req.file_path, TruePath)`, then sent `sizeof(req)` to the `MANPROXY` queue. The Qt consumer in `SandboxiePlus/QSbieAPI/SbieAPI.cpp` reads the field as a C string with `QString::fromWCharArray(req->file_path)`. |
| Data | `InteractiveWire.h`, `file_copy.c`, `SbieAPI.cpp`, `MAN_FILE_MIGRATION_REQ`, `file_path[256]`, `File_MigrateFile_GetMode`, `SbieDll_CallServerQueue`, `CSbieAPI::GetQueueReq`, and `QString::fromWCharArray(req->file_path)`. |
| Schema | `INTERACTIVE_FILE_MIGRATION_PATH_BOUNDS` says `InteractiveWire.h` owns the fixed 256-`WCHAR` request field; `file_copy.c` owns the producer that serializes `TruePath` before crossing the `MANPROXY` queue boundary; the producer must not use unbounded string copy into `file_path[256]`; the producer must zero the full request before sending it; and `file_path` must be NUL-terminated inside the fixed field. |
| Topology | `File_MigrateFile_GetMode` builds `MAN_FILE_MIGRATION_REQ`, sends it through `SbieDll_CallServerQueue("*MANPROXY_session", req, sizeof(req))`, `QueueServer` stores opaque bytes, and `CSbieAPI::GetQueueReq` maps `req->file_path` into the UI prompt. The queue carrier proves byte extent only; the fixed wire field owns string containment. |
| Logic Risk | `TruePath` is an NT path and can exceed the 255-character payload capacity of `file_path[256]`. An unbounded `wcscpy` can overwrite adjacent stack state before the request crosses the queue boundary. For shorter paths, sending the full fixed request without clearing it can leak padding and unused path tail bytes to the UI queue. |
| Official Shape | `docs/plan/srev-225-interactive-file-migration-path-bounds.md` records Microsoft StrSafe and Visual C++ CRT references showing that bounded string-copy APIs include destination capacity and that unbounded `wcscpy` cannot prove sufficient destination space. The local owner remains the fixed Sandboxie wire schema. |
| Fix | `File_MigrateFile_GetMode` now runs `memzero(&req, sizeof(req));`, caps `TruePath` to `ARRAYSIZE(req.file_path) - 1`, copies only that many characters with `wmemcpy`, and writes `req.file_path[path_chars] = L'\0'` before sending the request. No request id, queue name, copy-limit policy, file-size field, prompt decision, Qt request routing, or fixed wire layout changed. |
| Acceptance Gate | `docs/plan/check-srev-225.py` validates the draft-07 schema, official references, fixed wire shape, bounded/zeroed producer source shape, stale `wcscpy(req.file_path, TruePath)` removal, Qt C-string consumer topology, and ledger entry; `docs/plan/check-srev-225.sh` is the targeted wrapper. Runtime/build gate: Windows DLL and SandboxiePlus build; normal file migration prompt smoke; and over-255-character NT path smoke proving no overflow and a contained NUL-terminated truncated path. |
