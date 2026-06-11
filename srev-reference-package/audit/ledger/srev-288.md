---
kind: srev-ledger-entry
id: SREV-288
title: GDI GetStockObject SEH Failure Result
status: patched-comment-topology-after-official-getstockobject-and-seh-review-no-behavior-change
owner: Sandboxie/core/dll/gdi.c
spec: docs/plan/srev-288-gdi-getstockobject-seh-failure-result.md
schema: docs/plan/srev-288-gdi-getstockobject-seh-failure-result.schema.json
checker: docs/plan/check-srev-288.py
runtime_gate: Windows Chrome Chromium sandbox launch matrix on gdi32full GetStockObject builds including SYSTEM_FONT early GDI initialization and normal non-exception stock object queries
---

### SREV-288: GDI GetStockObject SEH Failure Result

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official GetStockObject and SEH review; no behavior change |
| Evidence | `Gdi_Full_Init_impl(..., full=TRUE)` resolves `GetStockObject` from `gdi32full.dll` and hooks it. `Gdi_GetStockObject` initializes `rc = 0`, calls `__sys_GetStockObject(fnObject)` inside `__try`, and sets `rc = 0` in `__except (EXCEPTION_EXECUTE_HANDLER)`. The old source comment framed this as a Chrome crash workaround and broad GDI initialization theory rather than the narrow native-call exception-to-failure-result boundary. |
| Data | `Gdi_Full_Init`, `Gdi_Full_Init_impl`, `GetProcAddress("GetStockObject")`, `SBIEDLL_HOOK(Gdi_, GetStockObject)`, `Gdi_GetStockObject`, `fnObject`, `__sys_GetStockObject`, `EXCEPTION_EXECUTE_HANDLER`, `HGDIOBJ rc`, and `NULL` failure result. |
| Schema | `GDI_GETSTOCKOBJECT_SEH_FAILURE_RESULT` says `GetStockObject` returns a stock-object handle on success and `NULL` on failure; `Gdi_GetStockObject` owns only the exception-to-NULL boundary around the native `GetStockObject` call; the hook is registered only from full GDI initialization after `GetProcAddress` resolves `GetStockObject`; SEH must remain narrow around `__sys_GetStockObject(fnObject)`; this SREV changes comments and proof only. |
| Topology | `gdi32full.dll load -> Gdi_Full_Init(module) -> Gdi_Full_Init_impl(module, TRUE) -> GetProcAddress("GetStockObject") -> SBIEDLL_HOOK(Gdi_, GetStockObject) -> Gdi_GetStockObject -> __sys_GetStockObject`. |
| Logic Risk | Generic crash/workaround wording can misroute future changes into broad browser-specific GDI policy. The local contract is smaller: guard one native `GetStockObject` call and return the documented failure value if that call raises during early GDI initialization. |
| Official Shape | Microsoft documents `GetStockObject` as returning a stock object handle on success and `NULL` on failure. Microsoft documents `__try` / `__except` and `EXCEPTION_EXECUTE_HANDLER` as frame-based SEH that transfers control to the handler and continues execution in that stack frame. |
| Fix | Comment-only source clarification. The source now names SREV-288, the full-GDI hook owner, the Chrome sandbox initialization context, the documented `GetStockObject` `NULL` failure result, and the narrow native-call SEH guard. No hook registration, exception filter, return value, or stock-object selector behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-288.py` validates the draft-07 schema, official references, full-GDI hook topology, source comment, narrow `__try` / `__except (EXCEPTION_EXECUTE_HANDLER)` shape, `rc = 0` failure result, stale workaround/crash wording removal from the function, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-288.sh` is the targeted wrapper. Runtime gate: Windows Chrome/Chromium sandbox launch matrix on builds where `gdi32full.dll` owns `GetStockObject`, including `SYSTEM_FONT` access during early GDI initialization and negative smoke for normal non-exception stock object queries. |
