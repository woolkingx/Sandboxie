---
kind: srev-ledger-entry
id: SREV-194
title: Protected Root API String Contract
status: patched-source-level-after-official-probeforread-and-bounded-string-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/file_flt.c
spec: docs/plan/srev-194-protected-root-api-string-contract.md
schema: docs/plan/srev-194-protected-root-api-string-contract.schema.json
checker: docs/plan/check-srev-194.py
runtime_gate: Windows driver build plus mount unmount protected-root valid unterminated oversized empty malformed-pointer and allocation-failure proof
---
### SREV-194: Protected Root API String Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `ProbeForRead` and bounded string shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/drv/file.h` was the top unnamed reviewable core file after SREV-193. It declares `File_Api_ProtectRoot` and `File_Api_UnprotectRoot`. `Sandboxie/core/svc/MountManager.cpp` calls these through `SbieApi_Call`, which passes raw pointer values through the driver API buffer. Before this fix, `Sandboxie/core/drv/file_flt.c` used unbounded `wcslen` on `reg_root` and `file_root` API pointer arguments, copied `reg_root` into fixed `MAX_REG_ROOT_LEN` buffers, and returned success if protected-root allocation failed. |
| Data | `File_Api_ProtectRoot`, `File_Api_UnprotectRoot`, `API_PROTECT_ROOT`, `API_UNPROTECT_ROOT`, `reg_root`, `file_root`, `MAX_REG_ROOT_LEN`, `PROTECTED_ROOT`, `ProbeForRead`, and the `SbieApi_Call` pointer argument crossing. |
| Schema | `PROTECTED_ROOT_API_STRING_CONTRACT` says `reg_root` must terminate within `MAX_REG_ROOT_LEN`, `file_root` must terminate within the driver cap, exact bounded string bytes must be probed before copy, unbounded `wcslen` is not legal on protected-root API pointer arguments, and allocation failure must not be reported as successful protection. |
| Topology | Legal flow is `MountManager request -> service terminator validation -> SbieApi_Call raw pointer arguments -> Api_FastIo_DEVICE_CONTROL captures ULONG64 values -> File_Api_ProtectRoot/File_Api_UnprotectRoot bounded terminator gate -> ProbeForRead exact bytes -> PROTECTED_ROOT copy -> File_ProtectedRoots list`. |
| Logic Risk | Service-side validation is not the driver owner gate. The driver was re-reading user-mode service pointers and relying on unbounded string scans after the API crossing. An unterminated or oversized registry root could overrun the fixed driver buffer, and an allocation failure could silently leave protection absent while returning success. |
| Official Shape | `docs/plan/srev-194-protected-root-api-string-contract.md` records Microsoft `ProbeForRead` and bounded string-length references. `docs/plan/srev-194-protected-root-api-string-contract.schema.json` records the JSON Schema draft-07 local `PROTECTED_ROOT_API_STRING_CONTRACT` contract. |
| Fix | `file_flt.c` now uses `File_ProtectedRootStringLen` before protected-root copies, requires `reg_root` to terminate within `MAX_REG_ROOT_LEN`, requires non-empty `file_root` to terminate within a bounded driver cap, probes exact bounded string bytes before copying, removes `wcslen` from the protect/unprotect handlers, and returns `STATUS_INSUFFICIENT_RESOURCES` when allocation fails. |
| Acceptance Gate | `docs/plan/check-srev-194.py` validates the draft-07 schema, official references, `file.h` entry declarations, source helper, bounded gates, `ProbeForRead` coverage, stale unbounded `wcslen` removal, allocation-failure status, and split ledger fragment; `docs/plan/check-srev-194.sh` is the matrix wrapper. Runtime gate: Windows driver build plus mount/unmount protected-root valid, unterminated, oversized, empty, malformed-pointer, and allocation-failure proof. |
