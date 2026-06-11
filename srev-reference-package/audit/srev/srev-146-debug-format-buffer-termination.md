# SREV-146: Debug Format Buffer Termination

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/debug.c`, `Sandboxie/core/dll/SboxDll.vcxproj`, Microsoft `_vsnprintf` documentation |
| Output artifact | `docs/plan/srev-146-debug-format-buffer-termination.schema.json`, `docs/plan/check-srev-146.py`, `docs/plan/check-srev-146.sh`, ledger fragment |
| Owner | DLL-side debug formatting helpers `DbgPrint` and `DbgTrace` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows DLL build/runtime proof remains required |

## Evidence

`Sandboxie/core/dll/debug.c` became the top unnamed reviewable core file after
SREV-145. The active project file defines `WITH_DEBUG`, so the debug helper
block is part of the DLL build surface, not dead source text.

`DbgPrint` and `DbgTrace` format variadic input through `P_vsnprintf`, which is
resolved from ntdll as `_vsnprintf`. Before this SREV, both functions passed the
full `sizeof(tmp1)` count into `_vsnprintf` and then treated `tmp1` as a
null-terminated string through `OutputDebugStringA` or `%S` conversion into a
wide monitor string.

Official reference:

- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/vsnprintf-vsnprintf-vsnprintf-l-vsnwprintf-vsnwprintf-l?view=msvc-170

## Data

`WITH_DEBUG`, `DbgPrint`, `DbgTrace`, `P_vsnprintf`, `_vsnprintf`, `tmp1[510]`,
`OutputDebugStringA`, `Sbie_snwprintf`, and `SbieApi_MonitorPutMsg`.

## Schema

`DEBUG_FORMAT_BUFFER_TERMINATION` says:

- `DbgPrint` and `DbgTrace` own the local debug-format buffer before passing it
  to string-consuming debug or monitor APIs.
- `_vsnprintf` is a counted writer but does not guarantee null termination when
  output is truncated.
- The local buffer must reserve one byte for a terminator by passing
  `sizeof(tmp1) - 1` as the count.
- The local buffer must be initialized before `_vsnprintf` and must have the
  final byte set to `'\0'` after `_vsnprintf`.
- This SREV does not change debug hook installation, monitor categories, trace
  routing, or any non-debug sandbox policy decision.

## Topology

Legal debug-format flow:

```text
caller variadic debug format
  -> DbgPrint / DbgTrace stack char buffer
  -> _vsnprintf writes at most sizeof(tmp1)-1 bytes
  -> local terminator is forced at tmp1[sizeof(tmp1)-1]
  -> OutputDebugStringA or Sbie_snwprintf consumes a bounded string
```

## Logic Risk

Microsoft documents `_vsnprintf` as not null-terminating the buffer on
truncation. A debug trace path that treats a truncated buffer as a C string can
read past the stack buffer while producing debug output or converting to the
wide monitor message.

This is not a sandbox policy change and not a user/kernel boundary change. The
owner-local fix is to make the debug helper's local string contract explicit.

## Fix

`DbgPrint` and `DbgTrace` now initialize `tmp1[0]`, call `P_vsnprintf` with
`sizeof(tmp1) - 1`, and force `tmp1[sizeof(tmp1) - 1] = '\0'` before any string
consumer reads the buffer.

## Acceptance Gate

`docs/plan/check-srev-146.py` validates the draft-07 schema, official reference,
`WITH_DEBUG` project definition, both `DbgPrint` and `DbgTrace` termination
patterns, and the ledger fragment. `docs/plan/check-srev-146.sh` is the matrix
wrapper.

Runtime/build gate: Windows DLL build with `WITH_DEBUG`; long formatted debug
strings through `DbgPrint` and `DbgTrace` truncate cleanly without reading past
`tmp1`; normal short debug strings still reach `OutputDebugStringA` and
`SbieApi_MonitorPutMsg`.
