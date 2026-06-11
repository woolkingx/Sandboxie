---
kind: srev-ledger-entry
id: SREV-188
title: Conf Expand Early Exit Pool Lifetime
status: patched-source-level-after-official-pool-allocation-lifetime-review-needs-windows-driver-runtime-proof
owner: Sandboxie/core/drv/conf_expand.c
spec: docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.md
schema: docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.schema.json
checker: docs/plan/check-srev-188.py
runtime_gate: Windows driver build plus Driver Verifier or pool-tag observation for too-long and recursion-limit expansion failures
---
### SREV-188: Conf Expand Early Exit Pool Lifetime

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official pool allocation lifetime review; needs Windows driver runtime proof |
| Evidence | `Sandboxie/core/drv/conf_expand.c` was the highest-ranked unnamed reviewable core file after SREV-187. `Conf_Expand_2` allocates a per-expansion page buffer with `ExAllocatePoolWithTag(PagedPool, PAGE_SIZE, tzuk)` and normally releases it with `ExFreePoolWithTag`. Before this SREV, the `TooLong` and recursion-limit branches returned `NULL` directly, bypassing that release. The recursion branch also returned after `Conf_Expand_Helper` produced a new allocated expansion string and after the previous expansion string had already been freed. |
| Data | `Sandboxie/core/drv/conf_expand.c`, `Conf_Expand_2`, `Conf_Expand_Helper`, `Conf_Expand_Buffer`, `ExAllocatePoolWithTag`, `ExFreePoolWithTag`, `Mem_AllocString`, `Mem_FreeString`, `TooLong`, `Recursion`, and `model_value`. |
| Schema | `CONF_EXPAND_EARLY_EXIT_POOL_LIFETIME` says `Conf_Expand_2` owns the per-expansion page buffer; `Conf_Expand_Buffer` is allocated with `ExAllocatePoolWithTag(PagedPool, PAGE_SIZE, tzuk)`; every successful allocation must reach `ExFreePoolWithTag`; expansion strings allocated after `model_value` must be released with `Mem_FreeString` when expansion fails; too-long and recursion gates must fail closed without leaking the page buffer or current expansion string; expansion variable lookup, registry lookup, recursion limit, string length limit, and logging must not change. |
| Topology | Legal lifetime flow is `Conf_Expand_2` -> allocate `Conf_Expand_Buffer` -> loop over `Conf_Expand_Helper` results -> on normal success return allocated expanded string -> on too-long or recursion failure free current allocated string if needed -> common `ExFreePoolWithTag(Conf_Expand_Buffer, tzuk)` -> return final result or `NULL`. |
| Logic Risk | The old direct returns made failure paths skip their owner cleanup. A repeated too-long or recursive configuration expansion could leak one page-sized paged-pool buffer per attempt; the recursion branch could also leak the newly allocated expansion string. |
| Official Shape | `docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.md` records Microsoft `ExAllocatePoolWithTag` and `ExFreePoolWithTag` references. `docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.schema.json` records the JSON Schema draft-07 local `CONF_EXPAND_EARLY_EXIT_POOL_LIFETIME` contract. |
| Fix | The `TooLong` and `Recursion` branches now release any current allocated expansion string when it is not caller-owned `model_value`, set `new_value` to `NULL`, and break to the common `ExFreePoolWithTag` release path. No expansion lookup order, recursion limit, string length limit, registry query shape, or log message changed. |
| Acceptance Gate | `docs/plan/check-srev-188.py` validates the draft-07 schema, official references, `Conf_Expand_2` allocation and common release topology, removal of direct early returns, too-long and recursion cleanup, and ledger fragment; `docs/plan/check-srev-188.sh` is the matrix wrapper. Runtime gate: Windows driver build plus Driver Verifier or pool-tag observation for too-long and recursion-limit expansion failures. |
