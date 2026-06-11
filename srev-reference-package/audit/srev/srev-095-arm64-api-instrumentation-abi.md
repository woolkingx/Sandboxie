# SREV-095: ARM64 API Instrumentation ABI

## Data

`Sandboxie/core/dll/util_arm.asm` owns the native ARM64 API tracing trampoline
that runs when `Dll_ApiTrace` wraps a detour through `ApiInstrumentationAsm`.
The comment-admitted shape is:

```text
Dll_ApiTrace detour emitted by dllhook.c
trace entry header in x17
ApiInstrumentationAsm
saved x0-x7 argument frame
saved fp/lr pair
saved x16/x17 scratch pair
ApiInstrumentation(pName, pArgs)
final branch to traced detour target
```

## Official Shape

Microsoft documents Windows ARM64 as following AArch64 ABI conventions with
Windows-specific rules. The integer-register table defines `x0-x8` as volatile
parameter/result scratch registers, `x9-x15` as volatile scratch registers,
`x16-x17` as volatile intra-procedure-call scratch registers, `x18` as reserved
for the platform and pointing at the TEB in user mode, `x19-x28` as
non-volatile, `x29/fp` as non-volatile frame pointer, and `x30/lr` as the link
register.

Microsoft documents ARM64 parameter assignment as using the first general
registers for integral and pointer arguments, with `x0` carrying the first
pointer argument and `x1` carrying the second pointer argument for
`ApiInstrumentation(const char *pName, void **pStack)`.

Microsoft documents the ARM64 stack as always 16-byte aligned on Windows, with
hardware stack-alignment faults enabled for SP-relative accesses. The same page
also reserves only the 16-byte area immediately below the current stack pointer
for dynamic patching scenarios; this stub allocates stack with paired pre-index
stores instead of writing below an unchanged `SP`.

Microsoft documents ARM64 exception unwinding through `.xdata` unwind codes and
dynamic function tables for dynamically generated code. This SREV does not add a
new dynamic function table; it only classifies the existing fixed assembly
trampoline shape.

```text
https://learn.microsoft.com/en-us/cpp/build/arm64-windows-abi-conventions
https://learn.microsoft.com/en-us/cpp/build/arm64-exception-handling
https://learn.microsoft.com/en-us/windows/arm/arm64ec-abi
```

## Schema

Local schema:

```text
docs/plan/srev-095-arm64-api-instrumentation-abi.schema.json
```

The ARM64 API instrumentation contract is:

```text
dllhook.c emits ARM64 trace detours with x17 pointing at the trace entry header
ApiInstrumentationAsm preserves x0-x7 before calling ApiInstrumentation
ApiInstrumentationAsm passes pName in x0 and the saved argument frame in x1
the saved argument frame begins at the saved x0/x1 pair
pArgs[-1] is the saved LR consumed by ApiInstrumentation as ReturnAddress
ApiInstrumentationAsm preserves x16/x17 across the call before branching to the detour target
ApiInstrumentationAsm keeps SP 16-byte aligned across all stack accesses and the C call
this SREV does not change ApiTrace runtime behavior
```

## Topology

```text
Dll_ApiTrace
  -> dllhook.c emits trace entry
  -> ldr x17, NewDetour
  -> ldr x16, ApiInstrumentationAsm
  -> br x16
  -> ApiInstrumentationAsm saves x0-x7 and fp/lr
  -> x0 = x17 + 8 as pName
  -> x1 = saved x0/x1 frame as pArgs
  -> save x16/x17
  -> bl ApiInstrumentation
  -> restore x16/x17, fp/lr, x0-x7
  -> ldr x16, [x17]
  -> br x16 to detour target
```

## Logic Risk

The old `; todo` sat directly before a fully implemented ABI bridge. Treating it
as missing behavior would invite a risky rewrite of a live trampoline. The
official ABI instead shows the existing local shape is intentional: trace entry
state is passed in volatile `x17`, original call arguments live in volatile
`x0-x7`, and the C instrumentation call must receive its own `x0/x1` arguments
without losing the original target state.

The remaining runtime risk is not source shape but observation: ARM64 ApiTrace
must be exercised on real Windows ARM64 to prove the traced target still receives
the original argument registers and that the monitor receives the expected API
trace entry.

## Fix

Comment-only source clarification. The stale `; todo` was replaced with the
actual ABI contract: `x17` points at the trace entry header emitted by
`dllhook.c`; the saved `x0-x7` frame begins at `[sp+16]`; and `pArgs[-1]` is the
saved `LR` that `ApiInstrumentation` reads as `ReturnAddress`.

No runtime behavior was changed.

## Acceptance Gate

`docs/plan/check-srev-095.py` validates the draft-07 schema, official
references, `dllhook.c` ARM64 trace-detour emission, `util_arm.asm`
argument/scratch-register preservation, stale TODO removal, `trace.c`
`ApiInstrumentation` `pStack[-1]` consumption, and ledger entry.
`docs/plan/check-srev-095.sh` is the matrix wrapper.

Runtime gate: Windows ARM64 ApiTrace smoke where a traced API receives original
`x0-x7` argument values, `ApiInstrumentation` logs the expected function name,
`ReturnAddress` maps to the saved `LR`, recursion guard still suppresses nested
trace loops, and the final branch reaches the intended detour target.
