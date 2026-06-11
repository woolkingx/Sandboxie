---
kind: srev-ledger-entry
id: SREV-137
title: Ldr Init Entrypoint Instruction Cache Coherency
status: patched-source-needs-windows-entrypoint-runtime
owner: Sandboxie/core/dll/ldr_init.c
spec: docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.md
schema: docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.schema.json
checker: docs/plan/check-srev-137.py
runtime_gate: Windows x86, WoW64/x64, ARM64, and host-injection entrypoint runtime proof
---

### SREV-137: Ldr Init Entrypoint Instruction Cache Coherency

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official VirtualProtect/FlushInstructionCache and local entrypoint patch/restore analysis; needs Windows x86, WoW64/x64, ARM64, and host-injection runtime proof |
| Evidence | `Sandboxie/core/dll/ldr_init.c` was the highest-ranked unnamed reviewable core file after SREV-136. `Ldr_Inject_Init` saves original image-entrypoint bytes, changes page protection with `VirtualProtect(... PAGE_EXECUTE_READWRITE ...)`, and writes an architecture-specific entrypoint stub. Before this SREV, only the ARM64 branch called `NtFlushInstructionCache`; x86 and x64 entrypoint stub writes had no instruction-cache boundary before the patched entrypoint could execute. `Ldr_Inject_Entry` later restores the saved entrypoint bytes and returns the original entrypoint to the assembly handoff; before this SREV, only the ARM64 build flushed the restored entrypoint bytes. Microsoft documents `VirtualProtect` as making the caller responsible for cache coherency through `FlushInstructionCache` when executable code has been set in place, and documents `FlushInstructionCache` as required when applications generate or modify code in memory because the CPU may execute old cached code. |
| Data | `Ldr_Inject_Init`, `Ldr_Inject_Entry`, `Ldr_Inject_SaveBytes`, `Ldr_Inject_OldProtect`, `LDR_INJECT_NUM_SAVE_BYTES`, image entrypoint bytes, architecture-specific patch stubs, restored original entrypoint bytes, `VirtualProtect`, `PAGE_EXECUTE_READWRITE`, and `NtFlushInstructionCache`. |
| Schema | `LDR_INIT_ENTRYPOINT_INSTRUCTION_CACHE_COHERENCY` says `Ldr_Inject_Init` owns the initial executable entrypoint stub write; `Ldr_Inject_Entry` owns restoring the original executable entrypoint bytes; every architecture writes exactly `LDR_INJECT_NUM_SAVE_BYTES` bytes for the entrypoint mutation range; every entrypoint mutation must be followed by `NtFlushInstructionCache` over `entrypoint, LDR_INJECT_NUM_SAVE_BYTES`; the flush happens after code bytes are written and before the entrypoint patch is treated as published; the restore flush happens after original bytes are copied and protection is restored; and this SREV does not change patch bytes, entrypoint address calculation, host injection policy, F-Secure stack-zero compatibility, or DLL loading order. |
| Topology | Initial patch flow is image entrypoint, save original bytes, `VirtualProtect(... PAGE_EXECUTE_READWRITE ...)`, write architecture-specific entrypoint stub, `NtFlushInstructionCache(entrypoint, LDR_INJECT_NUM_SAVE_BYTES)`, then patched entrypoint may execute. Restore flow is patched entrypoint reaches `Ldr_Inject_Entry`, choose architecture-specific entrypoint address, `VirtualProtect(... PAGE_EXECUTE_READWRITE ...)`, copy saved original bytes, restore `Ldr_Inject_OldProtect`, `NtFlushInstructionCache(entrypoint, LDR_INJECT_NUM_SAVE_BYTES)`, then assembly stub returns or jumps to the original entrypoint. |
| Logic Risk | Entrypoint injection mutates executable code, not ordinary data. Without an instruction-cache flush on x86 and x64, the source can report a successful entrypoint patch or restore while the CPU is still permitted to execute old cached bytes. The local fix is to close the same cache boundary for every architecture without altering the patch bytes or injection state machine. |
| Official Shape | `docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.md` records Microsoft `VirtualProtect` and `FlushInstructionCache` references. `docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.schema.json` records the JSON Schema draft-07 local `LDR_INIT_ENTRYPOINT_INSTRUCTION_CACHE_COHERENCY` contract. |
| Fix | `Ldr_Inject_Init` now calls `NtFlushInstructionCache` after the architecture-specific entrypoint stub bytes are written for ARM64, x64, and x86. `Ldr_Inject_Entry` now calls `NtFlushInstructionCache` after restoring the saved entrypoint bytes and restoring the original protection for ARM64, x64, and x86. |
| Acceptance Gate | `docs/plan/check-srev-137.py` validates the draft-07 schema, official references, source placement of the initial-patch flush after all architecture stub writes, source placement of the restore flush after `memcpy` and protection restore, preservation of patch-byte patterns and saved-byte flow, and ledger entry; `docs/plan/check-srev-137.sh` is the matrix wrapper. Runtime/build gate: Windows x86, WoW64/x64, ARM64, and host-injection smoke must prove the entrypoint patch runs, original entrypoint bytes are restored, and the process reaches the original executable entrypoint without stale instruction-cache behavior. |
