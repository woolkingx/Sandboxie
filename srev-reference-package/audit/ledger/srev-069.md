---
kind: srev-ledger-entry
id: SREV-069
title: SXS ActCtx Temp Buffer Gate
status: patched-source-level-after-official-createactctxw-actctxw-wmemcpy-shape-and-loca
owner: Sandboxie/core/dll/sxs.c
spec: docs/plan/srev-069-sxs-actctx-temp-buffer-gate.md
schema: docs/plan/srev-069-sxs-actctx-temp-buffer-gate.schema.json
checker: docs/plan/check-srev-069.py
runtime_gate: "boxed manifest alternate path translation, normal `CreateActCtxW` fallback, `ActivationContextDetailedInformation` path post-processing, and low-memory temp allocation failure paths"
---
### SREV-069: SXS ActCtx Temp Buffer Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official CreateActCtxW/ACTCTXW/wmemcpy shape and local SXS temp-buffer analysis; needs Windows SXS activation-context runtime proof |
| Evidence | `Sandboxie/core/dll/sxs.c` derives temporary wide-string buffers from `ACTCTXW.lpSource`, boxed-path translation, and queried activation-context paths. Microsoft documents `CreateActCtxW` as consuming `ACTCTXW`, `ACTCTXW.lpSource` as a null-terminated path string, and `wmemcpy` as copying into caller-provided destination buffers. Before this patch, `args.Directory`, `MySource`, and `TruePath2` allocation failures could be followed by local writes or path APIs using null destination buffers. |
| Data | `ACTCTXW.lpSource`, `ACTCTXW.lpAssemblyDirectory`, `args.SourcePath`, `args.Directory`, alternate-path `MySource`, queried-path `TruePath2`, local `wmemcpy` calls, `SbieDll_GetHandlePath`, and fallback `__sys_CreateActCtxW`. |
| Schema | `SXS_ACTCTX_TEMP_BUFFER_GATE` says local SXS temp buffers are legal write destinations only after `Dll_AllocTemp` returns non-null. If alternate path translation cannot allocate `MySource`, only Sandboxie's local translation is skipped and the underlying `CreateActCtxW` owner receives the original `ACTCTXW`. |
| Topology | `ACTCTXW` inputs flow into Sandboxie's optional SXS path projection, then into temporary buffers, then to either the underlying `CreateActCtxW` call or QueryActCtx path post-processing. Sandboxie owns only its temp buffers and must prove them before writes. |
| Logic Risk | A low-memory temp-buffer allocation failure should not crash inside the compatibility wrapper. Without explicit gates, local path projection can dereference null before the real activation-context API owner receives the request. |
| Official Shape | `docs/plan/srev-069-sxs-actctx-temp-buffer-gate.md` records Microsoft `CreateActCtxW`, `ACTCTXW`, and `wmemcpy` references. `docs/plan/srev-069-sxs-actctx-temp-buffer-gate.schema.json` records the JSON Schema draft-07 local `SXS_ACTCTX_TEMP_BUFFER_GATE` contract. |
| Fix | `Sxs_CreateActCtxW` now gates `args.Directory` before copying `args.SourcePath`; `Sxs_CreateActCtxW_Alt` gates `MySource` before `SbieDll_GetHandlePath` and falls through to `__sys_CreateActCtxW` if local translation allocation fails; `Sxs_QueryActCtxW_2` gates `TruePath2` before trailing-slash copy. |
| Acceptance Gate | `docs/plan/check-srev-069.py` validates the draft-07 schema, official references, temp-buffer gates before writes, alternate translation skip/fallthrough, query-path trailing-slash allocation gate, and ledger entry; `docs/plan/check-srev-069.sh` is the matrix wrapper. Windows gate: boxed manifest alternate path translation, normal `CreateActCtxW` fallback, `ActivationContextDetailedInformation` path post-processing, and low-memory temp allocation failure paths. |
