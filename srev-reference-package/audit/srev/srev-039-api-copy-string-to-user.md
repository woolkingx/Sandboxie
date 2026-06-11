# SREV-039: API Copy String To User Counted String

## Finding

`Sandboxie/core/drv/api.c` exposes `Api_CopyStringToUser`, a shared helper that
writes driver-owned strings into user `UNICODE_STRING64` buffers. The helper
assumed every caller passed a valid byte count including a trailing NUL and a
valid source pointer. It also accepted odd `MaximumLength` values from the user
descriptor before writing a WCHAR string and setting a counted `Length`.

Current callers pass normal NUL-terminated WCHAR strings, but the helper itself
is the owner of this write-back boundary and should reject impossible string
shapes before copying into user memory.

## Official Shape

- `UNICODE_STRING.Length` and `MaximumLength` are byte counts; if the string is
  NUL-terminated, `Length` does not include the trailing NUL:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`
- `ProbeForWrite` validates a user buffer using a byte length and required
  alignment. If `Length` is zero, it does no address checking:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-039-api-copy-string-to-user.schema.json
```

The helper accepts a driver-owned WCHAR byte length that includes the trailing
NUL to copy. Legal non-empty output must be WCHAR-aligned, at least one WCHAR,
have a non-NULL source string, fit inside user `MaximumLength`, and have a
non-NULL user `Buffer`. `UNICODE_STRING64.Length` is updated to exclude the
trailing NUL.

## Fix

`Api_CopyStringToUser` now rejects odd `len`, nonzero `len < sizeof(WCHAR)`,
nonzero output with a NULL source string, odd user `MaximumLength`, and nonzero
output with a NULL user buffer. It still raises `STATUS_BUFFER_TOO_SMALL` when
the output does not fit.

## Acceptance Gate

`docs/plan/check-srev-039.py` validates the local schema, official references,
source guard order, and current caller surface.

Windows gate still needed: `API_GET_HOME_PATH`, process/box path query, and
config query with normal output, too-small buffers, odd `MaximumLength`, and
NULL-buffer/nonzero-length user descriptors.
