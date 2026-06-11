---
kind: srev-ledger-entry
id: SREV-208
title: memmem Bounded Search Contract
status: patched-source-level-after-official-buffer-compare-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/util.h
implementation: Sandboxie/core/drv/util.c
spec: docs/plan/srev-208-memmem-bounded-search-contract.md
schema: docs/plan/srev-208-memmem-bounded-search-contract.schema.json
checker: docs/plan/check-srev-208.py
runtime_gate: Windows driver build plus a kernel/unit probe or equivalent source-level test for NULL zero-length oversized-pattern no-match and match cases
---

### SREV-208: memmem Bounded Search Contract

| Field | Content |
|---|---|
| Severity | [moderate] |
| Status | patched source-level after official buffer compare shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/drv/util.h` was the top unnamed reviewable core file after SREV-207. It declares shared driver utility helpers, including the local `memmem` byte-search helper implemented in `Sandboxie/core/drv/util.c`. Before this fix, `memmem` computed `pBuf + nBufSize - nPatternSize` before checking whether `pSearchBuf` and `pPattern` were non-NULL and before proving that `nPatternSize <= nBufSize`. When the pattern was larger than the search buffer, that endpoint calculation could underflow the size expression and build an invalid search bound before the function had established its legal data shape. |
| Data | `util.h`, `util.c`, `memmem`, `pSearchBuf`, `nBufSize`, `pPattern`, `nPatternSize`, `pBuf`, `pEos`, and `memcmp`. |
| Schema | `MEMMEM_BOUNDED_SEARCH_CONTRACT` says `util.h` declares the shared driver `memmem` helper contract; `util.c` owns the implementation; search and pattern pointers must be validated before any pointer arithmetic or dereference; zero-length search or pattern requests return NULL; a pattern larger than the search buffer returns NULL before endpoint calculation; and `memcmp` may only run after the bounded search window is proven legal. |
| Topology | Legal flow is `driver caller -> memmem(pSearchBuf, nBufSize, pPattern, nPatternSize) -> null/zero/size-order gate -> pEos endpoint calculation inside the search buffer -> byte scan -> memcmp only inside the proven window`. |
| Logic Risk | The old endpoint calculation happened before the helper had proven that the search range could contain the pattern. A larger pattern could create an invalid end pointer and make the subsequent loop boundary meaningless. A NULL pattern could also reach `*(UCHAR*)pPattern` or `memcmp`. |
| Official Shape | `docs/plan/srev-208-memmem-bounded-search-contract.md` records Microsoft `memcmp` and buffer-overrun references. `docs/plan/srev-208-memmem-bounded-search-contract.schema.json` records the JSON Schema draft-07 local `MEMMEM_BOUNDED_SEARCH_CONTRACT` contract. |
| Fix | `memmem` now rejects NULL pointers, zero sizes, and `nPatternSize > nBufSize` before computing `pEos`. The existing byte scan and `memcmp` equality test are unchanged after the input shape is proven. |
| Acceptance Gate | `docs/plan/check-srev-208.py` validates the draft-07 schema, official references, `util.h` declaration, source-level guard ordering in `util.c`, the absence of the stale pre-gate endpoint calculation, the unchanged `memcmp` search loop after the gate, and the split ledger fragment; `docs/plan/check-srev-208.sh` is the targeted wrapper. Runtime/build gate: Windows driver build plus a kernel/unit probe or equivalent source-level test for NULL, zero-length, oversized-pattern, no-match, and match cases. |
