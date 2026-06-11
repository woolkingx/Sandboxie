# SREV-164: x64 Syscall Count Width

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/drv/util_asm.asm, Sandboxie/core/drv/syscall.c, Sandboxie/core/drv/syscall_win32.c, and Microsoft x64 ABI documentation
output artifact: x64 syscall trampoline reads the 32-bit syscall argument count through 32-bit registers
owner: Sandboxie/core/drv/util_asm.asm
acceptance gate: docs/plan/check-srev-164.py and docs/plan/check-srev-164.sh
```

## Data

`util_asm.asm` owns the low-level assembly helpers used by the driver. The
highest-risk path in this file is `Sbie_InvokeSyscall_asm`, which receives:

```c
NTSTATUS Sbie_InvokeSyscall_asm(void* func, ULONG count, void* args);
```

`syscall.c` and `syscall_win32.c` call this helper to dispatch selected kernel
and win32k syscall functions through an assembly proxy. The proxy copies up to
19 pointer-sized arguments from the caller-supplied `args` array, places the
first four arguments in `rcx`, `rdx`, `r8`, and `r9`, copies remaining arguments
to stack slots, then calls `func`.

Before this SREV, the x64 helper compared and copied the `ULONG count` through
full 64-bit `rdx`, `r10`, and `rcx`. That made the local assembly contract
stricter than the Microsoft x64 ABI: a 32-bit integer argument is right-justified
in the register, and the callee should access the portion of the register
needed for that type.

## Official Shape

- Microsoft documents the x64 calling convention as passing the first four
  integer arguments in `RCX`, `RDX`, `R8`, and `R9`:
  `https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170`.
- The same page documents that integer arguments in registers are
  right-justified, so the callee can ignore upper bits and access only the
  register portion needed by the argument type:
  `https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170#parameter-passing`.
- Microsoft documents x64 unwind/prolog/epilog constraints for non-leaf
  functions:
  `https://learn.microsoft.com/en-us/cpp/build/prolog-and-epilog?view=msvc-170`.

## Schema

`X64_SYSCALL_COUNT_WIDTH` says:

- `util_asm.asm` owns the assembly implementation of `Sbie_InvokeSyscall_asm`.
- The C-facing count parameter is `ULONG count`.
- On x64, `count` arrives as the low 32 bits of `RDX`; the high 32 bits are not
  part of the `ULONG` contract.
- The x64 trampoline must validate, store, compare, and load the count through
  32-bit register views: `edx`, `r10d`, and `ecx`.
- The count remains capped at 19 arguments before any stack copy.
- Register argument layout, stack argument layout, shadow-space placement,
  nonvolatile register preservation, and x86 trampoline behavior are unchanged.
- Linux source gates are not Windows driver build/runtime proof.

## Topology

Legal x64 syscall trampoline flow:

```text
Syscall_Invoke / Syscall_Invoke32
  -> Sbie_InvokeSyscall_asm(func, ULONG count, args)
  -> count validated through edx <= 19
  -> count stored in r10d
  -> args[4..count-1] copied with ecx rep count
  -> args[0..3] loaded into rcx/rdx/r8/r9
  -> call func
```

The assembly helper is a boundary adapter. It must not become the owner of
syscall policy, win32k filtering, token setup, trap-frame handling, or exception
translation.

## Logic Risk

Using full 64-bit register state for a 32-bit ABI parameter can let undefined or
stale high bits change the validation path or the `rep movsq` count. In the
worst case, a legal low 32-bit count could be treated as a larger 64-bit value
and return `STATUS_INVALID_SYSTEM_SERVICE`, or a polluted count could copy too
many stack arguments. The fix is to consume only the ABI-owned low 32 bits.

## Fix

`Sbie_InvokeSyscall_asm` now compares `edx` against the 19-argument cap, stores
the count with `mov r10d, edx`, compares `r10d` against the four register
arguments, and loads the `rep movsq` count through `ecx`. The patch does not
alter the x86 trampoline, stack allocation size, register argument order, or the
call target selection in `syscall.c` / `syscall_win32.c`.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-164.py
bash docs/plan/check-srev-164.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-164.py &&
bash docs/plan/check-srev-164.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows x64 driver build; normal kernel syscall proxy smoke;
win32k syscall proxy smoke; argument-count boundary smoke for counts 0, 4, 5,
19, and over-19; HVCI-enabled smoke for the guarded indirect-call path.
