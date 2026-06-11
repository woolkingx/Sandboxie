---
kind: srev-ledger-entry
id: SREV-033
title: File Check Key Exists Wire String
status: patched-source-level-after-official-rtlinitunicodestring-unicode-string-ntopenke
owner: Sandboxie/core/svc/filewire.h
spec: docs/plan/srev-033-file-key-exists-wire.md
schema: docs/plan/srev-033-file-key-exists-wire.schema.json
checker: docs/plan/check-srev-033.py
runtime_gate: "HKLM/HKCU domains key probing still works, and malformed odd-length/missing-NUL/zero/oversized requests fail with `STATUS_INVALID_PARAMETER` before key-open"
---
### SREV-033: File Check Key Exists Wire String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official RtlInitUnicodeString/UNICODE_STRING/NtOpenKey contract analysis; needs Windows malformed-wire proof |
| Evidence | `Sandboxie/core/svc/filewire.h` documents `FILE_CHECK_KEY_EXISTS_REQ.KeyPath_len` as a byte count. `Sandboxie/core/dll/key_merge.c:557` assigned a WCHAR count, while `Sandboxie/core/svc/fileserver.cpp:1127-1148` only checked bounded bytes before passing `req->KeyPath` as a NUL-terminated string to `CheckBoxKeyPath`, `RtlInitUnicodeString`, and `NtOpenKey`. |
| Data | `FILE_CHECK_KEY_EXISTS_REQ` carries a sandbox registry key path as counted WCHAR bytes plus trailing NUL. |
| Schema | `KeyPath_len` is bytes, aligned to `sizeof(WCHAR)`, nonzero, inside `MSG_HEADER.length`, and includes a trailing NUL before C-string APIs may read it. |
| Topology | DLL key-merge probing crosses the SbieSvc file-server pipe into registry-key existence checks; the service converts wire bytes into an `OBJECT_ATTRIBUTES` key name. |
| Logic Risk | A sender length-unit drift can make service validation prove fewer bytes than the C-string APIs consume. A malformed request without a counted trailing NUL can drive `wcslen`/`RtlInitUnicodeString` past the validated message segment. |
| Official Shape | `docs/plan/srev-033-file-key-exists-wire.md` records Microsoft `RtlInitUnicodeString`, `UNICODE_STRING`, and `NtOpenKey` references. `docs/plan/srev-033-file-key-exists-wire.schema.json` records the small local wire string schema. |
| Fix | `key_merge.c` now sends `KeyPath_len` in bytes. `fileserver.cpp` now uses `FileServer_IsValidWireWString` to validate nonzero, aligned, in-message, NUL-terminated WCHAR wire strings before `CheckKeyExists` and adjacent file-server handlers pass them to C-string APIs. |
| Acceptance Gate | `docs/plan/check-srev-033.py` validates the schema, sender byte-count assignment, and service-side string gate; `docs/plan/check-srev-033.sh` is the matrix wrapper. Windows gate: HKLM/HKCU domains key probing still works, and malformed odd-length/missing-NUL/zero/oversized requests fail with `STATUS_INVALID_PARAMETER` before key-open. |
