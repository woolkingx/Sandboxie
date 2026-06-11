---
kind: srev-ledger-entry
id: SREV-328
title: SXS RpcSs Alt CreateActCtx Topology
status: source-comment-classified-after-official-createactctxw-shape-review-no-behavior-change
owner: Sandboxie/core/dll/sxs.c
spec: docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.md
schema: docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.schema.json
checker: docs/plan/check-srev-328.py
runtime_gate: Capture SandboxieRpcSs startup and SXS activation-context creation to prove the service process uses the alternate path without blocking on its own RPCSS_SXS queue, while normal sandboxed callers still use the queue path when available
---
### SREV-328: SXS RpcSs Alt CreateActCtx Topology

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | source comment classified after official `CreateActCtxW` activation-context shape review; no source behavior change |
| Evidence | `Sandboxie/core/dll/sxs.c` routes normal activation-context creation through `Sxs_CallService` and the `RPCSS_SXS` queue, while `SandboxieRpcSs`, AppContainer, `DisableBoxedWinSxS`, queue-unavailable forced-process fallback, and the `*UseAltCreateActCtx*` reply sentinel route to `Sxs_CreateActCtxW_Alt`. The alternate path optionally translates boxed `lpSource` paths, sets the TLS process-create guard around that translated path, and then calls `__sys_CreateActCtxW`. `Sandboxie/apps/com/RpcSs/sxs.c` implements the `RPCSS_SXS` queue and can return the sentinel when its private `SxsGenerateActivationContext` path succeeds with a zero section. |
| Data | `Sxs_UseAltCreateActCtx`, `Dll_ImageType == DLL_IMAGE_SANDBOXIE_RPCSS`, `Dll_AppContainerToken`, `DisableBoxedWinSxS`, `RPCSS_SXS`, `UseAltCreateActCtx`, `*UseAltCreateActCtx*`, `Sxs_CreateActCtxW_Alt`, `ACTCTXW lpSource`, optional boxed-path translation, and `__sys_CreateActCtxW`. |
| Schema | `SXS_RPCSS_ALT_CREATEACTCTX_TOPOLOGY` says `CreateActCtxW` owns the final activation-context handle; Sandboxie owns only the optional SXS service projection and boxed-path translation around `ACTCTXW`; `SandboxieRpcSs` must not synchronously re-enter the in-sandbox `RPCSS_SXS` service it implements; `Sxs_UseAltCreateActCtx` and the `*UseAltCreateActCtx*` sentinel are local topology gates to fall back to native `CreateActCtxW`; this SREV changes comments and proof only. |
| Topology | `normal sandboxed caller -> Sxs_CreateActCtxW -> Sxs_CallService -> RPCSS_SXS queue -> SandboxieRpcSs Sxs_Thread / Sxs_Request / Sxs_Generate -> RtlCreateActivationContext on returned section`; `SandboxieRpcSs or sentinel fallback -> Sxs_CreateActCtxW -> Sxs_CreateActCtxW_Alt -> optional boxed lpSource translation -> __sys_CreateActCtxW`. |
| Logic Risk | The old source comment described this as a generic workaround and said to use the real SXS from CSRSS. That wording hides the actual owner boundary: the service process implementing `RPCSS_SXS` cannot safely block on that same queue/thread during startup or loader-lock-sensitive work. Future changes should preserve the recursion/deadlock gate or reprove it with Windows runtime evidence. |
| Official Shape | `docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.md` records Microsoft `CreateActCtxW`, activation-context, and `ACTCTXW` references. `docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.schema.json` records the JSON Schema draft-07 local `SXS_RPCSS_ALT_CREATEACTCTX_TOPOLOGY` contract. |
| Fix | Comment-only source clarification. The source now names SREV-328 and states that `SandboxieRpcSs` avoids re-entering the in-sandbox SXS service. It also states that the alternate path calls the native `CreateActCtxW` owner after optional boxed-path translation, preserving the recursion gate. No `Sxs_UseAltCreateActCtx` predicate, `RPCSS_SXS` queue behavior, fallback sentinel, boxed-path translation, TLS process-create flag, `__sys_CreateActCtxW` call, or activation-context result handling changed. |
| Acceptance Gate | `docs/plan/check-srev-328.py` validates the draft-07 schema, official references, source comment, `Sxs_UseAltCreateActCtx` routing, native `__sys_CreateActCtxW` fallback, `RPCSS_SXS` service topology, fallback sentinel, stale generic workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-328.sh` is the targeted wrapper. Windows gate: SandboxieRpcSs startup and SXS activation-context creation should be captured to prove that the service process uses the alternate path without blocking on its own `RPCSS_SXS` queue, while normal sandboxed callers still use the queue path when available. |
