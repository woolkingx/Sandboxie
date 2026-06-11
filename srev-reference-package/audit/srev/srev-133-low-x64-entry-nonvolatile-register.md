# SREV-133: Low x64 Entry Nonvolatile Register

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/low/entry_asm.asm`, `Sandboxie/core/low/init.c`, Microsoft x64 ABI references |
| Output artifact | `docs/plan/srev-133-low-x64-entry-nonvolatile-register.schema.json`, `docs/plan/check-srev-133.py`, `docs/plan/check-srev-133.sh`, ledger row |
| Owner | x64 `_Start` lowlevel entry prelude |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows x64 lowlevel runtime remains required |

## Evidence

`Sandboxie/core/low/entry_asm.asm` was the highest-ranked unnamed reviewable core file after SREV-132. Its x64 `_Start` prelude saves the incoming `rcx`, `rdx`, `r8`, and `r9` arguments, computes position-independent pointers for `SbieLowData`, `_DetourCode`, and `_SystemService`, calls `EntrypointC`, restores the original four argument registers, then jumps to the `LdrInitializeThunk` trampoline returned in `rax`.

Before this SREV, `_Start` used `rbx` as a scratch copy of the call/pop base address but did not save or restore it before jumping to the trampoline. Microsoft documents the x64 calling convention as passing integer arguments in `RCX`, `RDX`, `R8`, and `R9`, treating `RAX`, `RCX`, `RDX`, `R8`, `R9`, `R10`, and `R11` as volatile, and treating `RBX`, `RBP`, `RDI`, `RSI`, `RSP`, and `R12`-`R15` as nonvolatile registers that must be saved and restored by a function that uses them.

Official references:

- https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/build/x64-software-conventions?view=msvc-170

## Data

`_Start`, `_001`, `SbieLowData`, `_DetourCode`, `_SystemService`, `EntrypointC`, original `rcx`, `rdx`, `r8`, `r9`, trampoline return in `rax`, scratch base register, `rbx`, `r10`, x64 volatile register set, x64 nonvolatile register set, and `LdrInitializeThunk` trampoline.

## Schema

`LOW_X64_ENTRY_NONVOLATILE_REGISTER` says:

- `_Start` is a detour prelude and must not clobber x64 nonvolatile registers before jumping to the `LdrInitializeThunk` trampoline.
- Windows x64 treats `RBX`, `RBP`, `RDI`, `RSI`, `RSP`, and `R12`-`R15` as nonvolatile registers.
- Windows x64 treats `RAX`, `RCX`, `RDX`, `R8`, `R9`, `R10`, and `R11` as volatile registers.
- `_Start` may use volatile scratch registers while preparing `EntrypointC` arguments.
- `_Start` preserves original `RCX`, `RDX`, `R8`, and `R9` arguments across `EntrypointC` before jumping to the trampoline.
- `_Start` computes `SbieLowData`, `_DetourCode`, and `_SystemService` relative to the call/pop base.
- `_Start` must not use `RBX` as an unbalanced scratch register.
- `SystemService` x64 keeps its own `RBX` and `RDI` save/restore contract unchanged.
- x86 `_Start` and `DetourCode` behavior are unchanged.

## Topology

The legal x64 entry topology is:

```text
patched LdrInitializeThunk entry
  -> _Start
  -> save original rcx rdx r8 r9 argument registers
  -> call/pop base into volatile scratch
  -> derive SbieLowData, _DetourCode, _SystemService
  -> call EntrypointC
  -> restore original rcx rdx r8 r9
  -> jump to returned LdrInitializeThunk trampoline
```

The nonvolatile register boundary is:

```text
_Start may clobber volatile scratch registers
_Start must not leave RBX/RBP/RDI/RSI/R12-R15 changed
```

## Logic Risk

Lowlevel entry code runs before the original loader entry continues. Even if this prelude is not a normal compiled function, it still lives on a Windows x64 ABI boundary: it calls `EntrypointC` and then transfers control to the original trampoline. Clobbering an unbalanced nonvolatile register in this path can corrupt loader or caller state in a way that only appears under specific startup/register pressure.

The correct local repair is to use a volatile scratch register for the call/pop base, not to add extra stack state or change the lowlevel section layout. `r10` is already volatile under the x64 ABI and is not one of the four original entry arguments restored before the trampoline jump.

## Fix

The x64 `_Start` path now uses `r10` instead of `rbx` to hold the call/pop base while deriving `SbieLowData`, `_DetourCode`, and `_SystemService`. No x86 path, `EntrypointC` signature, section layout, detour target, syscall bridge, or `SystemService` save/restore logic changed.

## Acceptance Gate

`docs/plan/check-srev-133.py` validates the draft-07 schema, official references, x64 `_Start` argument-save topology, volatile `r10` base use, stale unbalanced `rbx` scratch removal, original argument restore before trampoline jump, unchanged x86 `_Start`, unchanged `SystemService` `rbx` / `rdi` save/restore, and ledger entry. `docs/plan/check-srev-133.sh` is the matrix wrapper.

Runtime/build gate: Windows x64 lowlevel build, x64 sandbox process startup proving the `LdrInitializeThunk` trampoline receives original `rcx`, `rdx`, `r8`, and `r9`, debugger smoke proving `rbx` before `_Start` matches `rbx` at the trampoline jump, x64 syscall hook smoke proving `SystemService` still receives `SbieLowData`, and x86 startup smoke proving 32-bit behavior is unchanged.
