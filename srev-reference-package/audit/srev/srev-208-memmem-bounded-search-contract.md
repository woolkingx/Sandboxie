# SREV-208: memmem Bounded Search Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/drv/util.h` was the top unnamed reviewable core file after
SREV-207. It declares shared driver utility helpers, including the local
`memmem` byte-search helper implemented in `Sandboxie/core/drv/util.c`.

Before this fix, `memmem` computed `pBuf + nBufSize - nPatternSize` before
checking whether `pSearchBuf` and `pPattern` were non-NULL and before proving
that `nPatternSize <= nBufSize`. When the pattern was larger than the search
buffer, that endpoint calculation could underflow the size expression and build
an invalid search bound before the function had established its legal data
shape.

## Data

`util.h`, `util.c`, `memmem`, `pSearchBuf`, `nBufSize`, `pPattern`,
`nPatternSize`, `pBuf`, `pEos`, and `memcmp`.

## Official Shape

Microsoft documents `memcmp` as comparing the first `count` bytes of two
buffers. That makes both buffer pointers and the comparison count part of the
legal shape before the function is called.

Microsoft's buffer-overrun guidance says unchecked buffer operations can cause
corruption and that input should be validated and failed gracefully. For this
local helper, the legal shape is: non-NULL search buffer, non-NULL pattern,
non-zero sizes, and `nPatternSize <= nBufSize` before any end-pointer
calculation or `memcmp` call.

References:

- `https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcmp-wmemcmp?view=msvc-170`
- `https://learn.microsoft.com/en-us/windows/win32/secbp/avoiding-buffer-overruns`

## Schema

`MEMMEM_BOUNDED_SEARCH_CONTRACT` says:

- `util.h` declares the shared driver `memmem` helper contract.
- `util.c` owns the implementation.
- Search and pattern pointers must be validated before any pointer arithmetic
  or dereference.
- Zero-length search or pattern requests return NULL.
- A pattern larger than the search buffer returns NULL before endpoint
  calculation.
- `memcmp` may only run after the bounded search window is proven legal.

## Topology

```text
driver caller
-> memmem(pSearchBuf, nBufSize, pPattern, nPatternSize)
-> null/zero/size-order gate
-> pEos endpoint calculation inside the search buffer
-> byte scan
-> memcmp only inside the proven window
```

## Logic Risk

The old endpoint calculation happened before the helper had proven that the
search range could contain the pattern. A larger pattern could create an invalid
end pointer and make the subsequent loop boundary meaningless. A NULL pattern
could also reach `*(UCHAR*)pPattern` or `memcmp`.

## Fix

`memmem` now rejects NULL pointers, zero sizes, and `nPatternSize > nBufSize`
before computing `pEos`. The existing byte scan and `memcmp` equality test are
unchanged after the input shape is proven.

## Acceptance Gate

`docs/plan/check-srev-208.py` validates the draft-07 schema, official
references, `util.h` declaration, source-level guard ordering in `util.c`, the
absence of the stale pre-gate endpoint calculation, the unchanged `memcmp`
search loop after the gate, and the split ledger fragment. Runtime/build gate:
Windows driver build plus a kernel/unit probe or equivalent source-level test
for NULL, zero-length, oversized-pattern, no-match, and match cases.
