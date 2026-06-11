---
kind: srev-ledger-entry
id: SREV-205
title: MSCOREE CLR Entry Hook Boundary
status: classified-source-level-no-local-mutation-after-official-clr-loader-shape-review
owner: Sandboxie/core/dll/mscoree.c
spec: docs/plan/srev-205-mscoree-clr-entry-hook-boundary.md
schema: docs/plan/srev-205-mscoree-clr-entry-hook-boundary.schema.json
checker: docs/plan/check-srev-205.py
runtime_gate: Windows DLL build plus managed EXE smoke proving delayed injection runs once and the original _CorExeMain still starts the CLR
---

### SREV-205: MSCOREE CLR Entry Hook Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | classified source-level; no local mutation after official CLR loader shape review |
| Evidence | `Sandboxie/core/dll/mscoree.c` was the top unnamed reviewable core file after SREV-204. It hooks `mscoree.dll!_CorExeMain` so Sandboxie can run delayed injection initialization for managed executable images whose normal image entry point may be zero. Source review found that `MsCorEE_Init` resolves `_CorExeMain`, copies the resolved pointer to the hook source variable, and uses `SBIEDLL_HOOK`; the shared hook macro returns `FALSE` if hook installation does not return an original function pointer. |
| Data | `mscoree.c`, `MsCorEE_Init`, `MsCorEE__CorExeMain`, `DllName_mscoree`, `Ldr_GetProcAddrNew`, `SBIEDLL_HOOK`, `__sys__CorExeMain`, `_CorExeMain`, `Ldr_LoadInjectDlls`, `g_bHostInject`, `Dll_OsBuild`, and the local `ReadImageFileExecOptions` PEB byte workaround. |
| Schema | `MSCOREE_CLR_ENTRY_HOOK_BOUNDARY` says `_CorExeMain` is the managed executable loader entry; `mscoree.c` owns only the delayed Sandboxie injection edge before delegating to the original `_CorExeMain`; hook installation fails closed if the original cannot be resolved or captured; `Ldr_LoadInjectDlls` is called at most once from this hook instance; and the private PEB byte workaround remains a runtime compatibility dependency, not public API shape. |
| Topology | Legal flow is `managed EXE loader -> mscoree.dll!_CorExeMain -> Sandboxie hook MsCorEE__CorExeMain -> one-time PEB workaround and Ldr_LoadInjectDlls(g_bHostInject) -> original _CorExeMain -> CLR initialization and managed entrypoint`. |
| Logic Risk | The remaining risk is architectural rather than a deterministic local null-deref: the hook depends on CLR loader behavior and a private PEB byte workaround. This should stay visible as a runtime compatibility gate instead of being papered over with an unproven source patch. |
| Official Shape | `docs/plan/srev-205-mscoree-clr-entry-hook-boundary.md` records Microsoft `_CorExeMain`, `_CorValidateImage`, and CLR hosting references. `docs/plan/srev-205-mscoree-clr-entry-hook-boundary.schema.json` records the JSON Schema draft-07 local `MSCOREE_CLR_ENTRY_HOOK_BOUNDARY` contract. |
| Fix | No source mutation. The entry records the official CLR loader shape and local hook boundary so future review does not mistake `_CorExeMain` for an ordinary application entry point or patch the private PEB workaround without runtime evidence. |
| Acceptance Gate | `docs/plan/check-srev-205.py` validates the draft-07 schema, official references, local `_CorExeMain` hook topology, shared fail-closed hook macro, zero-entrypoint evidence in `ldr_init.c`, split ledger fragment, and absence of a source patch requirement; `docs/plan/check-srev-205.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build plus managed EXE smoke proving delayed injection runs once and the original `_CorExeMain` still starts the CLR. |
