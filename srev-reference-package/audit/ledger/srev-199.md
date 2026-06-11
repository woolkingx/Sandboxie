---
kind: srev-ledger-entry
id: SREV-199
title: SFC WRP Query Shim Contract
status: patched-source-level-after-official-sfc-wrp-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/sfc.c
spec: docs/plan/srev-199-sfc-wrp-query-shim-contract.md
schema: docs/plan/srev-199-sfc-wrp-query-shim-contract.schema.json
checker: docs/plan/check-srev-199.py
runtime_gate: Windows DLL build plus sandboxed SFC/WRP query smoke
---

### SREV-199: SFC WRP Query Shim Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official SFC/WRP shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/dll/sfc.c` was the top unnamed reviewable core file after SREV-198. The loader explicitly marks `sfc_os.dll` as `disable SFC`, and the shim intentionally returns not-protected / no-more-files results. The local issue was schema drift: `SfcIsFileProtected` was declared as `LPCWSTR *FileName`, while Microsoft documents the second argument as `LPCWSTR ProtFileName`; the init comment also named `SECUR32` instead of the SFC/WRP owner. |
| Data | `SfcIsFileProtected`, `SfcIsKeyProtected`, `SfcGetNextProtectedFile`, `RpcHandle`, `ProtFileName`, `SubKeyName`, `KeySam`, protected-file enumeration data, `ERROR_FILE_NOT_FOUND`, and `ERROR_NO_MORE_FILES`. |
| Schema | `SFC_WRP_QUERY_SHIM_CONTRACT` says the file query has documented `HANDLE, LPCWSTR` shape, the key query has documented `HKEY, optional LPCWSTR, REGSAM` shape, enumeration is presented as empty with `ERROR_NO_MORE_FILES`, and this SREV preserves the local disable-SFC compatibility policy. |
| Topology | Legal flow is `application or installer SFC/WRP query -> sfc_os.dll hook -> Sandboxie compatibility shim -> fixed not-protected / no-more-files result`. Windows owns real WRP policy; `sfc.c` owns only the sandbox compatibility projection. |
| Logic Risk | The old pointer-to-pointer prototype did not match the official API shape. Even where ABI width is unchanged, it creates a false schema for future policy work and makes review reason about an indirect string pointer that the API does not provide. |
| Official Shape | `docs/plan/srev-199-sfc-wrp-query-shim-contract.md` records Microsoft `SfcIsFileProtected`, `SfcIsKeyProtected`, `SfcGetNextProtectedFile`, WRP functions, and WRP resource-replacement references. `docs/plan/srev-199-sfc-wrp-query-shim-contract.schema.json` records the JSON Schema draft-07 local `SFC_WRP_QUERY_SHIM_CONTRACT` contract. |
| Fix | `sfc.c` now declares `SfcIsFileProtected` as `HANDLE RpcHandle, LPCWSTR ProtFileName` in the hook prototype, typedef, and implementation, and the init comment names SFC/WRP entry points. The not-protected / no-more-files compatibility policy remains unchanged. |
| Acceptance Gate | `docs/plan/check-srev-199.py` validates the draft-07 schema, official references, corrected `SfcIsFileProtected` shape, stale pointer-to-pointer/comment removal, preserved loader policy comment, preserved fixed return behavior, and split ledger fragment; `docs/plan/check-srev-199.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build plus sandboxed SFC/WRP query smoke. |
