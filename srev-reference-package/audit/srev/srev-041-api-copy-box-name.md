# SREV-041: API Copy Box Name Fixed String

## Finding

`Sandboxie/core/drv/api.c` exposes `Api_CopyBoxNameFromUser`, a shared helper
that copies a user box-name pointer into a local `BOXNAME_COUNT` buffer and then
calls `Box_IsValidName`. The helper probed `(BOXNAME_COUNT - 2)` WCHARs and used
`wcsncpy` into a zeroed local buffer. If the user input did not contain a NUL
terminator before that cap, the helper silently truncated the name and validated
the truncated local string instead of rejecting the malformed boundary input.

## Official Shape

- `ProbeForRead` validates user buffer access using a byte length and required
  alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-041-api-copy-box-name.schema.json
```

The helper consumes a user pointer to a NUL-terminated box-name C-string and
produces a kernel-owned `BOXNAME_COUNT` buffer. Legal input must be readable
under the existing fixed cap, WCHAR-aligned, non-empty, NUL-terminated before
`BOXNAME_COUNT - 2`, and valid under `Box_IsValidName`. Overlong unterminated
input is invalid, not a candidate for truncation.

## Fix

`Api_CopyBoxNameFromUser` now rejects NULL, empty, and overlong unterminated
input, copies one WCHAR at a time until the first NUL, probes using WCHAR
alignment, and no longer uses `wcsncpy` truncation before `Box_IsValidName`.

## Acceptance Gate

`docs/plan/check-srev-041.py` validates the schema, official reference, helper
copy order, removal of `wcsncpy`, and current caller surface.

Windows gate still needed: APIs using explicit box names with normal, empty,
invalid-character, and overlong unterminated names.
