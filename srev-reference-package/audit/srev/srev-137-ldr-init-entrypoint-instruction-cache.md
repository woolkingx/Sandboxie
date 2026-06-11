# SREV-137: Ldr Init Entrypoint Instruction Cache Coherency

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/ldr_init.c`, Microsoft `VirtualProtect` and `FlushInstructionCache` references, existing SREV-058 instruction-cache contract |
| Output artifact | `docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.schema.json`, `docs/plan/check-srev-137.py`, `docs/plan/check-srev-137.sh`, ledger fragment |
| Owner | `Sandboxie/core/dll/ldr_init.c` entrypoint patch/restore path |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows entrypoint injection runtime proof remains required |

## Evidence

`Sandboxie/core/dll/ldr_init.c` was the highest-ranked unnamed reviewable core
file after SREV-136. `Ldr_Inject_Init` copies original image-entrypoint bytes,
changes page protection with `VirtualProtect(... PAGE_EXECUTE_READWRITE ...)`,
then writes an architecture-specific entrypoint stub. Before this SREV, only
the ARM64 branch called `NtFlushInstructionCache`; x86 and x64 entrypoint stub
writes restored no instruction-cache boundary before the patched entrypoint
could execute.

`Ldr_Inject_Entry` later changes page protection again, restores the saved
entrypoint bytes with `memcpy`, restores the old page protection, and returns
the original entrypoint address to the assembly handoff. Before this SREV, only
the ARM64 build flushed the restored entrypoint bytes. x86 and x64 could publish
restored executable bytes without the cache-coherency gate.

Microsoft documents `VirtualProtect` as changing protection on committed pages
and says that when a protected region will be executable, the caller is
responsible for cache coherency through `FlushInstructionCache` after code is
set in place. Microsoft documents `FlushInstructionCache` as the call
applications should use when they generate or modify code in memory because the
CPU may otherwise execute old cached code.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache

## Data

`Ldr_Inject_Init`, `Ldr_Inject_Entry`, `Ldr_Inject_SaveBytes`,
`Ldr_Inject_OldProtect`, `LDR_INJECT_NUM_SAVE_BYTES`, image entrypoint bytes,
architecture-specific patch stubs, restored original entrypoint bytes,
`VirtualProtect`, `PAGE_EXECUTE_READWRITE`, and `NtFlushInstructionCache`.

## Schema

`LDR_INIT_ENTRYPOINT_INSTRUCTION_CACHE_COHERENCY` says:

- `Ldr_Inject_Init` owns the initial executable entrypoint stub write.
- `Ldr_Inject_Entry` owns restoring the original executable entrypoint bytes.
- Every architecture writes exactly `LDR_INJECT_NUM_SAVE_BYTES` bytes for the
  entrypoint mutation range.
- Every entrypoint mutation must be followed by `NtFlushInstructionCache` over
  `entrypoint, LDR_INJECT_NUM_SAVE_BYTES`.
- The flush happens after code bytes are written and before the entrypoint patch
  is treated as published.
- The restore flush happens after original bytes are copied and protection is
  restored.
- This SREV does not change patch bytes, entrypoint address calculation, host
  injection policy, F-Secure stack-zero compatibility, or DLL loading order.

## Topology

Initial patch flow:

```text
image entrypoint
  -> save original bytes
  -> VirtualProtect PAGE_EXECUTE_READWRITE
  -> write architecture-specific entrypoint stub
  -> NtFlushInstructionCache(entrypoint, LDR_INJECT_NUM_SAVE_BYTES)
  -> patched entrypoint may execute
```

Restore flow:

```text
patched entrypoint reaches Ldr_Inject_Entry
  -> choose architecture-specific entrypoint address
  -> VirtualProtect PAGE_EXECUTE_READWRITE
  -> memcpy saved original bytes
  -> restore Ldr_Inject_OldProtect
  -> NtFlushInstructionCache(entrypoint, LDR_INJECT_NUM_SAVE_BYTES)
  -> assembly stub returns/jumps to original entrypoint
```

## Logic Risk

Entrypoint injection mutates executable code, not ordinary data. Without an
instruction-cache flush on x86 and x64, the source can report a successful
entrypoint patch or restore while the CPU is still permitted to execute old
cached bytes. The local fix is to close the same cache boundary for every
architecture; it should not alter the patch bytes or injection state machine.

## Fix

`Ldr_Inject_Init` now calls `NtFlushInstructionCache` after the
architecture-specific entrypoint stub bytes are written for ARM64, x64, and
x86. `Ldr_Inject_Entry` now calls `NtFlushInstructionCache` after restoring the
saved entrypoint bytes and restoring the original protection for ARM64, x64,
and x86.

## Acceptance Gate

`docs/plan/check-srev-137.py` validates the draft-07 schema, official reference
links, source placement of the initial-patch flush after all architecture stub
writes, source placement of the restore flush after `memcpy` and protection
restore, preservation of patch-byte patterns and saved-byte flow, and the
ledger fragment. `docs/plan/check-srev-137.sh` is the matrix wrapper.

Runtime/build gate: Windows x86, WoW64/x64, ARM64, and host-injection smoke must
prove the entrypoint patch runs, original entrypoint bytes are restored, and the
process reaches the original executable entrypoint without stale
instruction-cache behavior.
