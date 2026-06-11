# SREV-042: Box Name Helper Routing

## Finding

After SREV-041 made `Api_CopyBoxNameFromUser` the local schema owner for
fixed-size user box-name strings, two driver API paths still duplicated the old
copy pattern:

- `Sandboxie/core/drv/session.c` `Session_Api_ForceChildren`
- `Sandboxie/core/drv/process_api.c` `Process_Api_Enum`

Both paths probed `(BOXNAME_COUNT - 2)` WCHARs and copied with `wcsncpy` into a
zeroed local buffer. That preserved the old silent truncation behavior for
overlong unterminated box-name input.

## Official Shape

- `ProbeForRead` validates user buffer access using a byte length and required
  alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-042-box-name-helper-routing.schema.json
```

Related box-name shape schema:

```text
docs/plan/srev-041-api-copy-box-name.schema.json
```

All explicit user box-name pointers in these APIs must route through
`Api_CopyBoxNameFromUser`. Process-owned box names remain trusted local state
when `Process_Api_Enum` is called from a sandboxed process.

## Fix

`Session_Api_ForceChildren` now rejects invalid explicit box names through
`Api_CopyBoxNameFromUser` before `Process_FcpInsert`. `Process_Api_Enum` now
uses the same helper when it needs to copy an explicit user box name and no
process-owned box is already selected.

## Acceptance Gate

`docs/plan/check-srev-042.py` validates that both API paths route explicit user
box names through `Api_CopyBoxNameFromUser` and no longer contain the duplicate
`ProbeForRead + wcsncpy` box-name copy pattern.

Windows gate still needed: ForceChildren and Process_Api_Enum with valid,
empty, invalid-character, and overlong unterminated explicit box names.
