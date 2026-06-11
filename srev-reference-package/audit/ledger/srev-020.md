---
kind: srev-ledger-entry
id: SREV-020
title: Driver GetFileName Object-Type Output Has ABI Shape Mismatch
status: patched-source-level-after-official-user-buffer-posture-and-local-abi-analysis-n
owner: "Sandboxie/core/drv/api_defs.h:386"
spec: docs/plan/srev-020-getfilename-type-output-abi.md
schema: docs/plan/srev-020-getfilename-type-output-abi.schema.json
checker: docs/plan/check-srev-020.sh
runtime_gate: driver API fuzz with 4-byte non-NULL fourth argument cannot overrun; normal NULL fourth-argument name queries still work
---
### SREV-020: Driver GetFileName Object-Type Output Has ABI Shape Mismatch

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official user-buffer posture and local ABI analysis; needs Windows runtime proof |
| Evidence | Explorer Hypatia reports driver API shape declares object type buffer as `WCHAR *` in `Sandboxie/core/drv/api_defs.h:386`, while public DLL header exposes `SbieApi_GetFileName(..., ULONG *ObjType)` at `Sandboxie/core/dll/sbieapi.h:271`; driver writes object type string in `Sandboxie/core/drv/file.c:2193`. |
| Data | Driver API output field for object type metadata. |
| Schema | Output must be either bounded string buffer or enum/integer, not both. |
| Topology | User-mode caller output pointer crosses METHOD_NEITHER driver API boundary. |
| Logic Risk | A caller following the public `ULONG*` declaration can receive a WCHAR string write into a 4-byte buffer. Current known internal callers pass NULL, so this is latent ABI risk. |
| Official Shape | `docs/plan/srev-020-getfilename-type-output-abi.md` records Microsoft METHOD_NEITHER, user-buffer probing, and exception-handling posture. |
| Fix | The old fourth argument is treated as reserved: `SbieApi_GetFileName` now names it `ObjTypeReserved`, and the driver rejects non-NULL `type_buf` with `STATUS_INVALID_PARAMETER` before any object-type string write. Existing in-tree callers pass NULL and keep the name-query path. |
| Acceptance Gate | `docs/plan/check-srev-020.sh` proves the unbounded `type_buf` write is gone and non-NULL type output fails closed before name output. Windows gate: driver API fuzz with 4-byte non-NULL fourth argument cannot overrun; normal NULL fourth-argument name queries still work. |
