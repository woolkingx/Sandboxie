# SREV-075: WriteProcessMemory Workaround Output Gate

## Data

`Sandboxie/core/dll/file_misc.c` contains a Firefox/Thunderbird compatibility
workaround in `File_WriteProcessMemory`. When those applications try to patch
selected `ntdll` routines, Sandboxie suppresses the real write and returns
success.

The relevant data nodes are:

```text
WriteProcessMemory caller arguments
Firefox / Thunderbird image type gate
target lpBaseAddress
optional lpNumberOfBytesWritten output pointer
local fake-success branch
real __sys_WriteProcessMemory fallback
```

## Official Shape

Microsoft documents `WriteProcessMemory` as taking an optional
`lpNumberOfBytesWritten` output pointer. If it is non-NULL, it receives the
number of bytes transferred; if it is NULL, it is ignored. Success returns
nonzero, failure returns zero and extended error is available through
`GetLastError`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-writeprocessmemory
```

## Schema

Local schema:

```text
docs/plan/srev-075-file-wpm-output-gate.schema.json
```

The workaround contract is:

```text
only Firefox / Thunderbird ntdll patch writes may enter the fake-success branch
NULL lpNumberOfBytesWritten is ignored
non-NULL lpNumberOfBytesWritten must be a writable caller output slot
bad output slots fail the wrapper instead of crashing inside the workaround
all non-workaround calls flow to the real WriteProcessMemory owner
```

## Topology

```text
caller WriteProcessMemory -> Sandboxie optional workaround -> output slot write -> success
caller WriteProcessMemory -> real Kernel32 WriteProcessMemory
```

Sandboxie owns only the compatibility bypass. It must preserve the observable
output-parameter shape when it chooses not to call the real API.

## Logic Risk

Before this patch, the fake-success path directly wrote `*lpNumberOfBytesWritten
= nSize` if the pointer was non-NULL. A bad caller output pointer could crash in
Sandboxie's workaround branch. The real API owner would otherwise own argument
validation and failure reporting.

## Fix

The fake-success path now writes `lpNumberOfBytesWritten` inside SEH. If the
output write raises an exception, the wrapper sets `ERROR_NOACCESS` and returns
`FALSE`. NULL output pointers remain ignored, and non-workaround calls still
fall through to `__sys_WriteProcessMemory`.

## Acceptance Gate

`docs/plan/check-srev-075.py` validates the draft-07 schema, official
`WriteProcessMemory` reference, Firefox/Thunderbird workaround scope, SEH-gated
output write, `ERROR_NOACCESS` failure, and unchanged real API fallback.

Windows gate: Firefox/Thunderbird suppressed ntdll patch write with NULL output,
valid output, and invalid output pointer; non-workaround writes still call the
real `WriteProcessMemory`.
