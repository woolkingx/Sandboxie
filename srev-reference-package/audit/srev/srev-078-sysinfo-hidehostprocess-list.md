# SREV-078: SysInfo HideHostProcess List Capacity

## Data

`Sandboxie/core/dll/sysinfo.c` builds a local multi-string list from repeated
`HideHostProcess` settings. `SysInfo_DiscardProcesses` later scans this list
while filtering `SYSTEM_PROCESS_INFORMATION` records.

The relevant data nodes are:

```text
HideHostProcess indexed config values
per-entry temporary name buffer
heap-owned multi-string list
used character count
allocated character capacity
process image-name comparison loop
final HeapFree
```

## Official Shape

Microsoft documents `HeapAlloc` as returning a block on success and NULL on
failure unless exception flags are used. `HeapReAlloc` may move the block, and
if it fails the original memory block remains valid. `HeapFree` frees memory
allocated by `HeapAlloc` / `HeapReAlloc`, and accepts NULL pointers.

```text
https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc
https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heaprealloc
https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapfree
```

## Schema

Local schema:

```text
docs/plan/srev-078-sysinfo-hidehostprocess-list.schema.json
```

The list contract is:

```text
the hidden-process list is a double-NUL-terminated WCHAR multi-string
capacity grows to fit configured HideHostProcess entries
HeapReAlloc failure preserves the old list and stops importing new entries
used length plus new entry plus final terminator must be checked before addition
consumer iteration walks only initialized entries until the final terminator
```

## Topology

```text
config HideHostProcess[n] -> temporary WCHAR buffer -> growable heap multi-string
growable heap multi-string -> process-list filtering loop -> HeapFree
```

`SysInfo_DiscardProcesses` owns only the transient hidden-process list used for
one process-list filtering pass.

## Logic Risk

Before this patch, the list had a fixed `100 * 110` WCHAR capacity and logged a
generic `HideProcess` message when the capacity was exceeded. That made the
actual policy shape depend on an arbitrary local guess: configured entries after
the capacity limit were silently skipped for the current filtering pass.

## Fix

The fixed-size buffer is now a growable heap multi-string. The code tracks used
length and capacity, grows with `HeapReAlloc` / `HeapAlloc` before copying a new
entry, preserves the old block on reallocation failure, and keeps the final
terminator after every copied entry.

## Acceptance Gate

`docs/plan/check-srev-078.py` validates the draft-07 schema, official heap
references, dynamic capacity fields, overflow guard, grow-before-copy topology,
`HeapReAlloc` / `HeapAlloc` use, stale fixed-capacity/log path removal, and
unchanged consumer iteration / final free.

Windows gate: `HideHostProcess` with 0 entries, a small list, more than 100
entries, and simulated allocation/reallocation failure keeps initialized list
entries valid and does not silently truncate due to a fixed local limit.
