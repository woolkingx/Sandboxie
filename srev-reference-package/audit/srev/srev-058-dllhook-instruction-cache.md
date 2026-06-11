# SREV-058: DLL Hook Instruction Cache Coherency

## Data

`Sandboxie/core/dll/dllhook.c` writes user-mode hook code at runtime. The x86/x64
hook path has three code-mutation surfaces:

```text
existing E9 jump target rewrite
new trampoline code buffer
source function detour bytes
```

The ARM64 path already restores page protection and flushes the source function
region plus trampoline code. The older x86/x64 path restored page protection
after writes but did not flush the instruction cache.

## Official Shape

Microsoft documents `VirtualProtect` as changing page protection on committed
pages and says code made executable or modified in executable memory requires
instruction-cache coherency through `FlushInstructionCache`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
```

Microsoft documents `FlushInstructionCache` as the API to call when applications
generate or modify code in memory:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
```

## Schema

Local schema:

```text
docs/plan/srev-058-dllhook-instruction-cache.schema.json
```

Every user-mode executable-code mutation must be followed by
`FlushInstructionCache` over the mutated code range before the mutated code can
be executed or returned to callers.

## Topology

```text
VirtualProtect writable/executable -> write hook bytes -> restore protection -> FlushInstructionCache
SbieApi_HookTramp writes trampoline -> FlushInstructionCache(trampoline)
```

`SbieDll_Hook_x86` owns the source-function patch and trampoline publication.
The CPU instruction cache is an execution boundary, not a C memory alias.

## Logic Risk

Before this patch, the x86/x64 hook path could write a new E9 operand, write
trampoline code, or overwrite source function bytes and then immediately return
a callable trampoline without flushing the instruction cache. On architectures
or configurations where instruction cache coherency is not automatic, the old
cached instructions may execute after the hook claims to be installed.

## Fix

The x86/x64 hook path now flushes:

```text
the rewritten E9 operand span
the 128-byte trampoline buffer after SbieApi_HookTramp
the source-function RegionBase/RegionSize after detour write and protection restore
```

## Acceptance Gate

`docs/plan/check-srev-058.py` validates the draft-07 schema, official reference
links, E9 operand flush, trampoline flush, source detour-region flush, existing
ARM64 flush precedent, and ledger entry.

Windows gate: user-mode x86, WoW64, x64 short-jump, and x64 vector-table hooks
should execute the newly written hook/trampoline code immediately after
installation without stale instruction-cache behavior.
