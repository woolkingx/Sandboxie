---
kind: srev-ledger-entry
id: SREV-058
title: DLL Hook Instruction Cache Coherency
status: patched-source-level-after-official-virtualprotect-flushinstructioncache-and-loc
owner: Sandboxie/core/dll/dllhook.c
spec: docs/plan/srev-058-dllhook-instruction-cache.md
schema: docs/plan/srev-058-dllhook-instruction-cache.schema.json
checker: docs/plan/check-srev-058.py
runtime_gate: x86, WoW64, x64 short relative hook, and x64 vector-table hook install/execute without stale instruction-cache behavior
---
### SREV-058: DLL Hook Instruction Cache Coherency

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official VirtualProtect/FlushInstructionCache and local x86/x64 hook writer analysis; needs Windows x86/WoW64/x64 hook runtime proof |
| Evidence | `Sandboxie/core/dll/dllhook.c` writes user-mode executable hook code in `SbieDll_Hook_x86`: it can rewrite an existing E9 target operand, generate a 128-byte trampoline with `SbieApi_HookTramp`, and patch the source function detour region. The ARM64 hook path already flushes its jump table, source region, and trampoline code. The x86/x64 path restored page protection after code writes but did not flush the instruction cache. |
| Data | Existing E9 operand span, generated trampoline buffer, source function `RegionBase`/`RegionSize`, page protection state, and instruction-cache coherency for mutated executable bytes. |
| Schema | `DLLHOOK_INSTRUCTION_CACHE_COHERENCY` says every user-mode executable-code mutation must be followed by `FlushInstructionCache` over the mutated range before the hook is treated as installed or its trampoline is returned. |
| Topology | Hook installation changes page protection, mutates executable bytes, restores protection, then must cross the CPU instruction-cache boundary with `FlushInstructionCache`. |
| Logic Risk | A hook writer changes code, not plain data. Without an instruction-cache flush, the caller can observe successful hook installation while a CPU still executes stale cached instructions. This is especially risky because the trampoline pointer is returned immediately after mutation. |
| Official Shape | `docs/plan/srev-058-dllhook-instruction-cache.md` records Microsoft `VirtualProtect` and `FlushInstructionCache` references. `docs/plan/srev-058-dllhook-instruction-cache.schema.json` records the JSON Schema draft-07 local `DLLHOOK_INSTRUCTION_CACHE_COHERENCY` contract. |
| Fix | `SbieDll_Hook_x86` now flushes the rewritten E9 operand span, the generated 128-byte trampoline buffer after `SbieApi_HookTramp`, and the source function detour `RegionBase`/`RegionSize` span after restoring page protection. |
| Acceptance Gate | `docs/plan/check-srev-058.py` validates the draft-07 schema, official references, E9 operand flush, trampoline flush, source detour-region flush, existing ARM64 flush precedent, and ledger entry; `docs/plan/check-srev-058.sh` is the matrix wrapper. Windows gate: x86, WoW64, x64 short relative hook, and x64 vector-table hook install/execute without stale instruction-cache behavior. |
