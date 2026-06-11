# SREV-074: API Current Process Sentinel Width

## Data

Sandboxie's driver API carries arguments in fixed `ULONG64` slots. Several API
handlers accept a process handle or process-id-like `HANDLE` value and use
`IS_ARG_CURRENT_PROCESS` to recognize the special current-process sentinel.

The relevant data nodes are:

```text
API_ARGS ULONG64 slot
native NtCurrentProcess / ZwCurrentProcess sentinel
WOW64 32-bit caller sentinel
driver-side HANDLE comparison
Process_Find / ObReferenceObjectByHandle owner call
```

## Official Shape

Microsoft documents the 64-bit porting rule that handles and pointers must not
be tested by casting to `ULONG`; pointer-precision types such as `UINT_PTR` /
`ULONG_PTR` should be used for pointer-width values:

```text
https://learn.microsoft.com/en-us/windows/win32/winprog64/rules-for-using-pointers
https://learn.microsoft.com/en-us/windows/win32/winprog64/the-new-data-types
```

Microsoft also documents `ZwCurrentProcess` as returning a special `HANDLE`
value that represents the current process:

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/zwcurrentprocess
```

## Schema

Local schema:

```text
docs/plan/srev-074-api-current-process-sentinel.schema.json
```

The driver API wire contract is:

```text
native current-process sentinel: (ULONG_PTR)-1
WOW64 wire current-process sentinel: 0x00000000FFFFFFFF
all other 64-bit values are ordinary caller data
sentinel recognition must not truncate an arbitrary 64-bit value to ULONG
```

## Topology

```text
user API slot -> driver ULONG64 capture -> exact sentinel gate -> owner API logic
```

`api.h` owns the sentinel predicate. Callers in `ipc.c`, `process_api.c`, and
`file.c` should share the same predicate instead of open-coding width decisions.

## Logic Risk

Before this patch, `IS_ARG_CURRENT_PROCESS(h)` cast `h` to `ULONG` and compared
only the low 32 bits with `0xffffffff`. That preserves the intended WOW64
compatibility case, but it also treats any 64-bit value whose low 32 bits are
all ones as the current-process sentinel.

That is the wrong shape for a handle-like wire field: it turns a malformed or
crafted 64-bit argument into a privileged special value before the real handle
owner can validate it.

## Fix

`IS_ARG_CURRENT_PROCESS` now uses `ULONG_PTR` and accepts only the exact native
`-1` sentinel or the zero-extended 32-bit `0xffffffff` WOW64 sentinel. It no
longer matches arbitrary 64-bit values by truncation.

Later source-comment clarification: `driver.h` now names SREV-074 instead of a
generic hack alert. The header still suppresses legacy pointer/HANDLE cast
warnings globally, but driver API current-process sentinel handling is owned by
the width-exact `IS_ARG_CURRENT_PROCESS` predicate in `api.h`.

## Acceptance Gate

`docs/plan/check-srev-074.py` validates the draft-07 schema, official references,
local `driver.h` SREV-074 comment, pointer-width macro shape, absence of the
stale hack wording and `(ULONG)h == 0xffffffff` truncating predicate, and all
current predicate call sites.

Windows gate: 64-bit callers passing native `NtCurrentProcess`, WOW64 callers
passing 32-bit `NtCurrentProcess`, and malformed high-bit `...FFFFFFFF` values
through duplicate/process/file API paths.
