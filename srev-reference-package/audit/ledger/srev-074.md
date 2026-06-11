---
kind: srev-ledger-entry
id: SREV-074
title: API Current Process Sentinel Width
status: patched-source-level-after-official-64-bit-pointer-handle-rules-official-zwcurre
owner: Sandboxie/core/drv/driver.h
spec: docs/plan/srev-074-api-current-process-sentinel.md
schema: docs/plan/srev-074-api-current-process-sentinel.schema.json
checker: docs/plan/check-srev-074.py
runtime_gate: "native 64-bit current-process API calls, WOW64 current-process API calls, and malformed high-bit `...ffffffff` arguments through duplicate/process/file API paths"
---
### SREV-074: API Current Process Sentinel Width

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official 64-bit pointer/HANDLE rules, official ZwCurrentProcess sentinel shape, and local driver API wire-slot analysis; needs Windows WOW64/native driver API runtime proof |
| Evidence | `Sandboxie/core/drv/driver.h` carries shared warning suppressions for legacy pointer/HANDLE casts and now points at SREV-074 for the driver API current-process sentinel rule. `Sandboxie/core/drv/api.h` documented the specific API_ARGS problem: a 32-bit caller can pass a 32-bit `HANDLE` sentinel while the 64-bit driver compares with native `NtCurrentProcess`. Before this patch, `IS_ARG_CURRENT_PROCESS(h)` cast `h` to `ULONG` and matched only the low 32 bits. Microsoft documents that pointer/HANDLE values should not be tested by casting to `ULONG` on 64-bit Windows, pointer-precision types such as `ULONG_PTR` track pointer width, and `ZwCurrentProcess` returns a special current-process `HANDLE` value. |
| Data | Captured `ULONG64` API argument slots, native current-process sentinel, zero-extended WOW64 current-process sentinel, process/duplicate/file API call sites, and owner calls such as `Process_Find` / handle reference logic. |
| Schema | `API_CURRENT_PROCESS_SENTINEL_WIDTH` says the legal current-process sentinel shapes are the native pointer-width `-1` and the zero-extended 32-bit `0xffffffff` WOW64 wire value. Any other 64-bit value, even if its low 32 bits are `0xffffffff`, is caller data and must not become the current-process sentinel by truncation. |
| Topology | User API slots are captured into the driver as `ULONG64`; `api.h` owns the shared exact sentinel predicate; handlers in `ipc.c`, `process_api.c`, and `file.c` consume the predicate before crossing into process/handle-owner logic. |
| Logic Risk | The old truncating predicate preserved the intended WOW64 compatibility case but also accepted malformed or crafted 64-bit values with low bits set to all ones. That can route an invalid external argument into a privileged special-current-process branch before the real handle/process owner validates it. |
| Official Shape | `docs/plan/srev-074-api-current-process-sentinel.md` records Microsoft 64-bit pointer rules, new pointer-precision data types, and `ZwCurrentProcess` references. `docs/plan/srev-074-api-current-process-sentinel.schema.json` records the JSON Schema draft-07 local `API_CURRENT_PROCESS_SENTINEL_WIDTH` contract. |
| Fix | `IS_ARG_CURRENT_PROCESS` now uses `ULONG_PTR` and accepts only exact `(ULONG_PTR)-1` or exact `(ULONG_PTR)0xffffffff`, preserving native and WOW64 current-process forms while rejecting arbitrary 64-bit low-word matches. |
| Comment Contract | `driver.h` now names SREV-074 instead of a generic hack alert. The header warning suppressions remain unchanged, but current-process sentinel handling is owned by `api.h`'s width-exact predicate. |
| Acceptance Gate | `docs/plan/check-srev-074.py` validates the draft-07 schema, official references, `driver.h` SREV-074 comment, pointer-width macro shape, stale hack wording removal, stale `(ULONG)h == 0xffffffff` removal, and current macro call sites; `docs/plan/check-srev-074.sh` is the matrix wrapper. Windows gate: native 64-bit current-process API calls, WOW64 current-process API calls, and malformed high-bit `...ffffffff` arguments through duplicate/process/file API paths. |
