---
kind: srev-ledger-entry
id: SREV-352
title: SbieIni GET_DAT Reserved Wire Surface
status: patched-comment-classification-after-native-file-read-schema-review-no-behavior-change
owner: Sandboxie/core/svc/sbieiniserver.cpp
spec: docs/plan/srev-352-sbieini-get-dat-reserved-wire-surface.md
schema: docs/plan/srev-352-sbieini-get-dat-reserved-wire-surface.schema.json
checker: docs/plan/check-srev-352.py
runtime_gate: none for comment-only classification; future GET_DAT implementation requires Windows broker read smoke
---

### SREV-352: SbieIni GET_DAT Reserved Wire Surface

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/classification after native file read schema review; no behavior change |
| Evidence | `SbieIniServer::Handler2` has an active `MSGID_SBIE_INI_SET_DAT` route and a reserved `MSGID_SBIE_INI_GET_DAT` id. `SetDatFile` accepts an `SBIE_INI_SETTING_REQ`, limits the target to Sandboxie home-directory `*.dat` names without `..`, allows only the session leader, and uses the request value bytes as the file payload or deletes the file when `value_len` is zero. `sbieiniwire.h` defines generic setting request/reply shapes but no dat-file read reply shape. Local search found no caller that sends `MSGID_SBIE_INI_GET_DAT`. The inactive `GetDatFile` block carried a bare `ToDo`. |
| Data | `SbieIniServer::Handler2`, `SbieIniServer::SetDatFile`, `sbieiniserver.h`, `sbieiniwire.h`, `msgids.h`, `MSGID_SBIE_INI_SET_DAT`, `MSGID_SBIE_INI_GET_DAT`, `SBIE_INI_SETTING_REQ`, `SBIE_INI_SETTING_RPL`, session leader pid, Sandboxie home path, `*.dat` setting name, `NtDeleteFile`, `NtCreateFile`, `NtWriteFile`, and future `NtReadFile` shape. |
| Schema | `SBIEINI_GET_DAT_RESERVED_WIRE_SURFACE` says `MSGID_SBIE_INI_SET_DAT` remains the active Sandboxie home-directory dat write/delete route; `MSGID_SBIE_INI_GET_DAT` remains reserved and unrouted until a read reply schema exists; `sbieiniwire.h` currently has no dat-file read reply shape with file size, byte count, or partial-read contract; `SetDatFile` remains gated to the session leader and terminated `*.dat` names without parent traversal; a future `GET_DAT` route must define max read size, EOF behavior, reply buffer shape, and caller authorization before code is wired; this SREV changes comments and proof only. |
| Topology | `SET_DAT -> caller must be the session leader -> setting must be a terminated *.dat name without .. -> SbieApi_GetHomePath + setting builds the target path -> value_len == 0 deletes -> otherwise NtCreateFile(FILE_GENERIC_WRITE, FILE_OVERWRITE_IF) -> NtWriteFile(value, value_len)`. `GET_DAT -> reserved msgid -> no active handler -> future route requires reply schema, max read size, EOF behavior, and caller gate`. |
| Logic Risk | The stale `ToDo` can make the missing read route look like a simple feature hole. It is actually a schema gap: a read broker must decide how large a file may be, how the reply buffer represents bytes, which caller may read it, and whether the path policy is identical to `SET_DAT` or stricter. |
| Official Shape | Microsoft documents `NtCreateFile` as producing a file handle for later file operations, and documents `NtReadFile` as reading bytes into a caller-provided buffer with `IO_STATUS_BLOCK.Information` receiving the number of bytes read. That means readback needs an explicit reply shape and size gate rather than reusing the write request by analogy. |
| Fix | Comment-only source clarification. The source now names SREV-352, marks `MSGID_SBIE_INI_GET_DAT` as a reserved wire id, and names the missing read reply schema, length cap, file-size gate, and authorization model. No msgid, request structure, `SET_DAT` validation, home path construction, `NtDeleteFile`, `NtCreateFile`, `NtWriteFile`, or caller behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-352.py` validates the draft-07 schema, official references, reserved `GET_DAT` source comments, inactive route/prototype shape, active `SET_DAT` session-leader and path gates, absence of `GET_DAT` callers, stale `ToDo` removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-352.sh` is the targeted wrapper. Runtime gate: none for this comment-only classification. A future `GET_DAT` implementation would need a Windows broker read smoke with valid/invalid callers, missing file, large file, exact cap, delete/write/read sequencing, and malformed path names. |
