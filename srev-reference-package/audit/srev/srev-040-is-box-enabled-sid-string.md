# SREV-040: IsBoxEnabled SID String Boundary

## Finding

`Sandboxie/core/drv/conf_user.c` accepts optional
`API_IS_BOX_ENABLED_ARGS.sid_string` from user mode. When present, the handler
assigned `sid = args->sid_string.val` and passed that raw user pointer into
`Conf_IsBoxEnabled`, which eventually reads the SID string while resolving user
and group names. The existing `Api_CopySidStringFromUser` helper was not used by
this API path.

`Api_CopySidStringFromUser` also only probed a fixed 96-WCHAR range and copied
up to 94 WCHARs with `wcsncpy`; it did not require the input to be
NUL-terminated before the local cap, so an overlong user string could be
silently truncated into a different local SID string.

## Official Shape

- `ConvertStringSidToSidW` documents a string SID as a NUL-terminated
  string-format SID such as the standard `S-R-I-S-S...` form:
  `https://learn.microsoft.com/en-us/windows/win32/api/sddl/nf-sddl-convertstringsidtosidw`
- `ProbeForRead` validates user buffer access using a byte length and required
  alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-040-is-box-enabled-sid-string.schema.json
```

The optional `sid_string` field is a user pointer. Legal input must be readable
as the existing fixed 96-WCHAR local contract, NUL-terminated before the
94-WCHAR payload cap, non-empty, and begin with `S-` before policy logic reads
it. If `sid_string` is absent, the handler keeps using
`Process_GetSidStringAndSessionId` to obtain a kernel-owned SID string.

## Fix

`Conf_Api_IsBoxEnabled` now copies optional `sid_string` through
`Api_CopySidStringFromUser` into a local kernel buffer before calling
`Conf_IsBoxEnabled`. `Api_CopySidStringFromUser` now rejects NULL, empty, and
overlong unterminated input instead of silently truncating it.

## Acceptance Gate

`docs/plan/check-srev-040.py` validates the local schema, official references,
source copy/validation order, and that `Conf_Api_IsBoxEnabled` no longer passes
the raw user `sid_string` pointer into policy logic.

Windows gate still needed: `API_IS_BOX_ENABLED` with absent SID, valid explicit
SID, empty SID, overlong unterminated SID, and invalid-prefix SID.
