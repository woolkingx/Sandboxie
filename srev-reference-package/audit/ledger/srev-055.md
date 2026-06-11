---
kind: srev-ledger-entry
id: SREV-055
title: SYSFER Entry Point Patch Boundary
status: patched-source-level-after-official-pe-virtualprotect-flushinstructioncache-and-
owner: Sandboxie/core/dll/custom.c
spec: docs/plan/srev-055-custom-sysfer-entrypoint-patch.md
schema: docs/plan/srev-055-custom-sysfer-entrypoint-patch.schema.json
checker: docs/plan/check-srev-055.py
runtime_gate: valid SYSFER load patch, malformed/zero entry point skip, restored page protection, cache-coherent execution, and Symantec Endpoint Protection compatibility behavior
---
### SREV-055: SYSFER Entry Point Patch Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official PE/VirtualProtect/FlushInstructionCache and local SYSFER entry point patch analysis; needs Windows endpoint-protection compatibility proof |
| Evidence | `Sandboxie/core/dll/custom.c` `Custom_SYSFER_DLL` nullifies `SYSFER.DLL` by making its loaded image entry point writable and overwriting it with a `mov al, 1; ret` stub. The pre-patch code trusted `Ldr_OptionalHeader(base)`, patched `base + AddressOfEntryPoint` without checking the module base, DOS/NT signatures, non-zero entry point, or that the four-byte patch span fits inside `SizeOfImage`, and did not flush the instruction cache or restore the previous page protection. |
| Data | Loaded `SYSFER.DLL` module base, PE DOS/NT headers, `AddressOfEntryPoint` RVA, `SizeOfImage`, the four-byte return stub, page protection state, and instruction-cache coherency. |
| Schema | `CUSTOM_SYSFER_ENTRYPOINT_PATCH` says the entry point patch may run only for a valid loaded image whose non-zero entry point RVA names a four-byte span inside `SizeOfImage`; executable code mutation must flush the instruction cache and restore previous page protection. |
| Topology | The loader maps `SYSFER.DLL`; the PE headers define the legal entry point span; `Custom_SYSFER_DLL` temporarily changes page protection, writes exactly the compatibility patch span, flushes executable-code cache state, and restores protection. |
| Logic Risk | This is a compatibility patch on executable code. If the entry point RVA is malformed or zero, the patch can target the wrong memory. If the instruction cache is stale or the page remains writable/executable longer than necessary, the workaround can become a correctness and hardening regression. |
| Official Shape | `docs/plan/srev-055-custom-sysfer-entrypoint-patch.md` records Microsoft PE, `VirtualProtect`, and `FlushInstructionCache` references. `docs/plan/srev-055-custom-sysfer-entrypoint-patch.schema.json` records the JSON Schema draft-07 local `CUSTOM_SYSFER_ENTRYPOINT_PATCH` contract. |
| Fix | `Custom_SYSFER_DLL` now validates non-null module base, DOS signature, NT signature, non-zero entry point RVA, and patch span within `SizeOfImage`; the source comment points back to this SREV as the bounded entry-point patch owner; it changes protection only for `sizeof(ULONG)`, writes the stub, calls `FlushInstructionCache`, and restores the previous page protection. |
| Acceptance Gate | `docs/plan/check-srev-055.py` validates the draft-07 schema, official references, PE signature gates, bounded entry point span, exact-size `VirtualProtect`, instruction-cache flush, old protection restore, owner-boundary comment, removal of the unbounded `Ldr_OptionalHeader` trust path, and ledger entry; `docs/plan/check-srev-055.sh` is the matrix wrapper. Windows gate: valid SYSFER load patch, malformed/zero entry point skip, restored page protection, cache-coherent execution, and Symantec Endpoint Protection compatibility behavior. |
