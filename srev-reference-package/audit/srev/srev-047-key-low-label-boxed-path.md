# SREV-047: Key Low-Label Boxed Path

## Finding

`Sandboxie/core/drv/key.c` `Key_Api_SetLowLabel` takes a caller-provided
registry key path and applies `Driver_LowLabelSd` with
`ZwSetSecurityObject`. The local comment says the path must be inside the box,
but the pre-patch check used `Box_IsBoxedPath(proc->box, file, &objname)` and
allowed the path when that file-path predicate was false.

That mixed registry-key data with file-path topology and inverted the allow
condition before a security descriptor mutation.

The input shape also silently rounded odd `path_len` down with `& ~1` and
accepted embedded NULs before `RtlInitUnicodeString` converted the counted
payload into a NUL-terminated string.

## Official Shape

- `ZwOpenKey` opens an existing registry key by `OBJECT_ATTRIBUTES`, requires
  the requested access, and the driver must close the returned handle:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey`
- `ZwSetSecurityObject` sets an object's security state; DACL writes require
  `WRITE_DAC`, and the routine must run at `PASSIVE_LEVEL`:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwsetsecurityobject`

## Local Schema

Machine-readable JSON Schema draft-07 contract:

```text
docs/plan/srev-047-key-low-label-boxed-path.schema.json
```

`path_len` is a byte count and must be an even non-empty WCHAR payload under the
existing 512-WCHAR cap. `path_str` is copied into a kernel-owned buffer, with a
single synthesized terminator after the counted payload and no embedded NULs.
The path must match the sandbox key root via `Box_IsBoxedPath(proc->box, key,
...)` before any security descriptor mutation.

## Fix

`Key_Api_SetLowLabel` now rejects odd-length paths, allocation failure, and
embedded NULs. It checks the `key` sandbox root and allows only boxed registry
key paths before `ZwOpenKey` / `ZwSetSecurityObject`.

## Acceptance Gate

`docs/plan/check-srev-047.py` validates the draft-07 schema, official
references, even-length and embedded-NUL gates, key-root boxed-path check,
removal of the file-root/inverted predicate, and that the security mutation is
gated by boxed key topology.

Windows gate still needed: boxed key path succeeds, out-of-box registry key path
is denied, odd-length and embedded-NUL paths are invalid, and the low-label
security descriptor still applies to the intended boxed key.
