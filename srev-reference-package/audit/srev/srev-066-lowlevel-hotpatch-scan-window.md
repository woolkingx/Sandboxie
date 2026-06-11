# SREV-066: Low-Level Hotpatch Scan Window

## Data

`Sandboxie/core/dll/lowlevel_inject.c` searches for an 8-byte hotpatch table
inside a local buffer filled by `ReadProcessMemory`. If the first hotpatch area
near `LdrInitializeThunk` is not available, the helper reads a larger remote
range into `myBuffer` and scans for an 8-byte `0x90` or `0xcc` pattern.

The relevant data nodes are:

```text
remote read base address
myBuffer local byte capacity
ReadProcessMemory byte count
ULONG_PTR pattern width
scan start offset
selected remote hotpatch table address
```

## Official Shape

Microsoft documents `ReadProcessMemory` as copying `nSize` bytes from the
target process into the caller-provided output buffer, with
`lpNumberOfBytesRead` receiving the number of bytes transferred:

```text
https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory
```

The API defines the byte-transfer boundary. The local scanner owns all later
in-process buffer-window bounds.

## Schema

Local schema:

```text
docs/plan/srev-066-lowlevel-hotpatch-scan-window.schema.json
```

The scanner may test an `ULONG_PTR` pattern only when the full window fits:

```text
scan_offset + sizeof(ULONG_PTR) <= sizeof(myBuffer)
```

Because the remote hotpatch address is byte-oriented, the local scan offset must
also be byte-oriented.

## Topology

```text
remote process memory -> ReadProcessMemory -> local myBuffer -> ULONG_PTR scan window -> remote patch-table address
```

`ReadProcessMemory` owns the transfer into the local buffer. The local scanner
owns the pattern width and the mapping from byte offset to remote address.

## Logic Risk

Before this patch, the scan loop used `i < sizeof(myBuffer)` while reading an
`ULONG_PTR` at `&myBuffer[i]`. Since `myBuffer` is a `short[1024]`, `&myBuffer[i]`
is scaled by `sizeof(short)`, and the last valid offsets were not bounded by
the 8-byte pattern width. The final iterations could read beyond the local
buffer while searching a compatibility fallback path.

## Fix

The scan loop now uses a byte offset (`SIZE_T i`) and permits only windows where
`i + sizeof(ULONG_PTR) <= sizeof(myBuffer)`. Pattern reads use
`(UCHAR *)myBuffer + i`, and the selected remote table address still uses the
same byte offset. The remaining fallback comments now name SREV-066 instead of
generic hack wording; no allocation, read, protection, write, or selected-table
address behavior changed.

## Acceptance Gate

`docs/plan/check-srev-066.py` validates the draft-07 schema, official
`ReadProcessMemory` reference, byte-offset scan loop, bounded `ULONG_PTR`
window, byte-addressed pattern reads, absence of the stale `i < sizeof(myBuffer)`
window, removal of generic hack wording from this fallback scan block, and
ledger entry.

Windows gate: the normal nearby allocation path still wins when available; the
fallback hotpatch-table scan still finds an 8-byte `0x90`/`0xcc` slot when one
exists; repeated fallback attempts do not read past the local buffer.
