# SREV-048: IPC Query Symbolic Link Buffer

## Finding

`Sandboxie/core/drv/ipc.c` `Ipc_Api_QuerySymbolicLink` uses one user buffer for
two roles:

- input: symbolic-link object name;
- output: symbolic-link target returned by `ZwQuerySymbolicLinkObject`.

The pre-patch code divided `name_len` by `sizeof(WCHAR)` without rejecting odd
byte counts, copied the entire buffer capacity into the kernel name buffer, and
then used `RtlInitUnicodeString` to reinterpret that copy as a NUL-terminated
object name. On output it wrote back through the user buffer after
`ProbeForRead`, not `ProbeForWrite`.

The local API caller passes `name_len` as buffer capacity, not as the input
object-name payload length. Therefore the legal input shape is a
NUL-terminated object name inside that shared capacity, and the legal output
shape is a returned target that fits in the same capacity with one synthesized
NUL terminator.

## Official Shape

- `ZwOpenSymbolicLinkObject` opens an existing symbolic-link object and the
  returned handle must be closed when no longer used:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopensymboliclinkobject`
- `ZwQuerySymbolicLinkObject` writes a target string into an initialized
  `UNICODE_STRING`; `MaximumLength` and `Buffer` must be set before the call:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwquerysymboliclinkobject`

## Local Schema

Machine-readable JSON Schema draft-07 contract:

```text
docs/plan/srev-048-ipc-query-symbolic-link.schema.json
```

`name_len` is the shared user buffer capacity in bytes. It must be even,
non-empty, and no more than the existing 4096-WCHAR cap. The input name must be
non-empty and NUL-terminated inside that capacity. The kernel object-name copy
stops at the input terminator. Query output may overwrite the same user buffer
only if the returned target plus a synthesized NUL fits.

## Fix

`Ipc_Api_QuerySymbolicLink` now rejects odd `name_len`, empty input, and
unterminated input. It copies only through the first NUL into the kernel object
name. The `ZwQuerySymbolicLinkObject` target buffer still uses the full shared
capacity, but output writeback now requires target-plus-NUL capacity and probes
the user buffer with `ProbeForWrite`.

## Acceptance Gate

`docs/plan/check-srev-048.py` validates the draft-07 schema, official
references, byte-count alignment gate, bounded input terminator scan, removal
of full-capacity name copy, `ProbeForWrite` output, and target-plus-NUL fit
check.

Windows gate still needed: valid symbolic link query, odd `name_len`,
unterminated input, empty input, read-only output mapping, exact-fit target, and
too-small output buffer behavior.
