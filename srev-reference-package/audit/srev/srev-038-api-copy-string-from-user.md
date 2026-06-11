# SREV-038: API Copy String From User Counted String

## Finding

`Sandboxie/core/drv/api.c` exposes `Api_CopyStringFromUser`, a shared helper
that copies a user `UNICODE_STRING64` into a `Driver_Pool` string and appends a
local NUL terminator. The helper computed `Length + sizeof(WCHAR)` as the local
output size, then used that enlarged size to probe/copy from the user buffer
even though `UNICODE_STRING.Length` does not include the trailing NUL. It then
wrote the local terminator at `*len / sizeof(WCHAR)`, one WCHAR past the
allocated output block. The same helper also did not verify
`Length <= MaximumLength`, did not reject nonzero `Length` with a NULL buffer,
and returned a C-string view even if the counted payload contained an embedded
NUL.

The only current caller is `Conf_Api_Update`, where the returned string is later
stored through `Conf_Update` / `Conf_Add_Setting` as a NUL-terminated setting
value. That makes embedded NUL a schema violation, not a supported multi-string
encoding.

## Official Shape

- `UNICODE_STRING.Length` and `MaximumLength` are byte counts; if the string is
  NUL-terminated, `Length` does not include the trailing NUL:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`
- `ProbeForRead` validates user buffer access using a byte length and required
  alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-038-api-copy-string-from-user.schema.json
```

The helper consumes a counted WCHAR byte string from user mode and produces a
driver-owned C-string projection. Legal non-empty input must have a non-NULL
buffer, WCHAR-aligned byte length, and `Length <= MaximumLength`. Because the
output is a C-string view, an embedded NUL in the counted payload is invalid.

## Fix

`Api_CopyStringFromUser` now probes and copies only `UNICODE_STRING64.Length`
bytes from the user buffer, writes the local terminator at
`Length / sizeof(WCHAR)`, checks `Length <= MaximumLength`, rejects nonzero
length with a NULL buffer, avoids zero-length copies from a NULL user pointer,
rejects embedded NULs after copy, and releases/reset output ownership on that
malformed-input branch.

## Acceptance Gate

`docs/plan/check-srev-038.py` validates the local schema, official references,
source guard order, embedded-NUL cleanup branch, and the current `Conf_Api_Update`
caller.

Windows gate still needed: `API_UPDATE_CONF` with empty, normal, odd-length,
`Length > MaximumLength`, NULL-buffer/nonzero-length, and embedded-NUL setting
values.
