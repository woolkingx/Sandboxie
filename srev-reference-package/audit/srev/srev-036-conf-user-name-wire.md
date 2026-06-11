# SREV-036: Config User Name Counted String

## Finding

`Sandboxie/core/drv/conf_user.c` receives `API_SET_USER_NAME_ARGS.sidstring`
and `username` as user `UNICODE_STRING64*` values. The driver rounded odd byte
lengths down with `& ~1`, copied the counted bytes into `CONF_USER.space`, then
used `wcslen` to derive `sid_len` and `name_len`. If a counted string contained
an embedded NUL, `CONF_USER.name` could be placed before the full copied SID
segment ended, letting the username overwrite part of the copied SID bytes.

## Official Shape

- `UNICODE_STRING.Length` is a byte count; if the string is NUL-terminated, the
  trailing NUL is not included:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`
- `ProbeForRead` validates user buffer access using a byte length and alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`
- `ConvertStringSidToSidW` consumes a NUL-terminated string-format SID and
  returns a SID allocated for `LocalFree`:
  `https://learn.microsoft.com/en-us/windows/win32/api/sddl/nf-sddl-convertstringsidtosidw`
- `LookupAccountSid` returns account names as NUL-terminated strings and uses
  character-count buffer lengths:
  `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountsida`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-036-conf-user-name-wire.schema.json
```

The SbieSvc sender validates the SID string with `ConvertStringSidToSid` before
calling `SbieApi_SetUserName`. The driver receives counted WCHAR byte strings
and owns the persistent `CONF_USER` block. Legal input must be non-empty,
WCHAR-aligned, no larger than 1024 bytes, and not larger than `MaximumLength`.
Because `CONF_USER` stores local NUL-terminated strings after the copy, embedded
NULs are rejected before deriving `sid_len`, `name_len`, or the `name` storage
pointer.

## Fix

`Conf_Api_SetUserName` now rejects odd byte lengths, validates
`Length <= MaximumLength`, scans copied counted WCHAR segments for embedded NUL,
derives `sid_len` and `name_len` from the validated byte counts, and places
`CONF_USER.name` after the full counted SID segment plus one local trailing NUL.

## Acceptance Gate

`docs/plan/check-srev-036.py` validates the local schema, official references,
source counted-string guards, copied-buffer NUL rejection, and length derivation.

Windows gate still needed: service-driven `SbieApi_SetUserName` for a normal SID
and username, plus malformed odd-length, embedded-NUL, and stale
`MaximumLength` driver API probes.
