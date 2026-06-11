# SREV-033: File Check Key Exists Wire String

## Finding

`FILE_CHECK_KEY_EXISTS_REQ.KeyPath_len` is documented in `filewire.h` as a byte
count. One sender in `Sandboxie/core/dll/key_merge.c` built the request length
in bytes, but assigned `KeyPath_len` as a WCHAR count.

On the service side, `FileServer::CheckKeyExists` only checked that
`offset + KeyPath_len` stayed within `MSG_HEADER.length`, then passed
`req->KeyPath` to `CheckBoxKeyPath`, `RtlInitUnicodeString`, and `NtOpenKey` as
a NUL-terminated string.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey`
- `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`

Relevant contract:

- `RtlInitUnicodeString` initializes a `UNICODE_STRING` from a `PCWSTR` source
  string.
- `UNICODE_STRING.Length` is measured in bytes and does not include a trailing
  NUL when one exists.
- `ZwOpenKey` / `NtOpenKey` opens a registry key from `OBJECT_ATTRIBUTES`
  carrying the object name.

## Local Schema

Small machine-readable schema:

```text
docs/plan/srev-033-file-key-exists-wire.schema.json
```

Request:

```text
MSG_HEADER
KeyPath_len bytes, including trailing NUL WCHAR
KeyPath[KeyPath_len / sizeof(WCHAR)]
```

The service may only use `KeyPath` as a C-style source string after proving the
wire byte count is aligned, fits inside the message, and ends in `L'\0'`.

## Source Change

`FileServer_IsValidWireWString` now centralizes the service-side wire string
gate for file-server WCHAR strings:

- nonzero byte count;
- `<= PIPE_MAX_DATA_LEN`;
- aligned to `sizeof(WCHAR)`;
- no `offset + length` overflow;
- trailing `L'\0'` inside the counted segment.

`CheckKeyExists` uses this gate before `CheckBoxKeyPath` and
`RtlInitUnicodeString`. The same helper is also applied to the adjacent
file-server counted path handlers that already use NUL-terminated string APIs.

The `key_merge.c` sender now assigns `KeyPath_len = path_len * sizeof(WCHAR)`,
matching the existing request allocation and `filewire.h` byte-count contract.

## Acceptance Gate

Source-level gate:

- `docs/plan/check-srev-033.py` validates the schema, sender byte-count fix, and
  service-side string gate.
- `CheckKeyExists` must not use the old raw `offset + req->KeyPath_len`
  validation shape.

Windows runtime gate:

- Exercise HKLM/HKCU domains key probing through `Key_Merge`.
- Send malformed local harness requests for odd byte count, missing trailing
  NUL, zero length, and oversized length, then confirm `STATUS_INVALID_PARAMETER`
  before any key-open attempt.
