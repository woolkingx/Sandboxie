# SREV-094: Ldr Inject Stack-Zero Owner

## Data

`Sandboxie/core/dll/util_32.asm` and `Sandboxie/core/dll/util_64.asm` own the
architecture-specific entry stubs that run before the restored application
entrypoint. The comment-admitted shape is:

```text
patched image entrypoint
Ldr_Inject_Entry32 / Ldr_Inject_Entry64 asm stub
Ldr_Inject_Entry C owner
original entrypoint bytes restored by ldr_init.c
former injection stack frame
F-Secure compatibility requirement for zeroed stack residue
```

## Official Shape

Microsoft documents the x64 stack contract as saying memory beyond the current
`RSP` is volatile and can be overwritten by the OS, debugger, or interrupt
handler. It also says `RSP` must be set before reading or writing values in a
stack frame.

Microsoft documents x64 stack allocation as prolog-owned space for locals, saved
registers, stack parameters, and register parameters. The x64 calling convention
requires caller-allocated space for at least four register parameters and
requires the stack pointer to remain 16-byte aligned outside prolog/epilog
regions except for leaf functions.

Microsoft documents x64 prolog/epilog restrictions and says nonleaf functions
that allocate stack space, call functions, save nonvolatile registers, or use
exception handling need unwind-described prolog/epilog state. This injection
entry stub is a custom assembly boundary, so its stack mutation must stay simple,
bounded, and restored before jumping to the original entrypoint.

Microsoft documents x86 argument passing as stack-based and documents
`__stdcall` as callee-cleanup. Naked/custom-entry documentation describes custom
prolog/epilog code as the mechanism for functions called from non-C/C++
contexts, with local stack space allocated by adjusting `ESP`.

```text
https://learn.microsoft.com/en-us/cpp/build/stack-usage
https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention
https://learn.microsoft.com/en-us/cpp/build/prolog-and-epilog
https://learn.microsoft.com/en-us/cpp/cpp/argument-passing-and-naming-conventions
https://learn.microsoft.com/en-us/cpp/cpp/stdcall
https://learn.microsoft.com/en-us/cpp/cpp/naked-function-calls
https://learn.microsoft.com/en-us/cpp/cpp/rules-and-limitations-for-naked-functions
```

## Schema

Local schema:

```text
docs/plan/srev-094-ldr-inject-stack-zero-owner.schema.json
```

The stack-zero contract is:

```text
Ldr_Inject_Entry restores original entrypoint bytes and returns the original entrypoint address
the asm entry stub may clear the 0x200-byte former injection frame for F-Secure compatibility
the stack-zero operation must first allocate that 0x200-byte range by moving ESP/RSP
the stack-zero operation must restore ESP/RSP before returning or jumping to the original entrypoint
the x86 stub keeps the stdcall-style return to the restored entrypoint path
the x64 stub keeps the existing jump-to-returned-entrypoint path
this SREV does not change the patched entrypoint bytes or the F-Secure compatibility policy
```

## Topology

x86 topology:

```text
patched entrypoint call
  -> Ldr_Inject_Entry32
  -> push pRetAddr and call Ldr_Inject_Entry
  -> Ldr_Inject_Entry restores original entrypoint bytes and rewrites pRetAddr
  -> Ldr_Inject_Entry32 allocates 0x200 bytes, zeros that owned range, restores ESP
  -> ret to restored entrypoint
```

x64 topology:

```text
patched entrypoint jump
  -> Ldr_Inject_Entry64
  -> call Ldr_Inject_Entry
  -> Ldr_Inject_Entry restores original entrypoint bytes and returns entrypoint in RAX
  -> Ldr_Inject_Entry64 saves RAX in RDX
  -> Ldr_Inject_Entry64 allocates 0x200 bytes, zeros that owned range, restores RSP
  -> jmp RDX to restored entrypoint
```

## Logic Risk

The old source cleared `[esp/rsp - 0x200, esp/rsp)` after restoring the stack
pointer from the `Ldr_Inject_Entry` call frame. That writes to stack memory the
stub no longer owns. On x64, Microsoft's stack contract explicitly treats memory
beyond current `RSP` as volatile and says `RSP` must be set before stack-frame
access.

The compatibility behavior itself may be real: the local comment says some
injected F-Secure code assumes zeroed stack residue. The fix therefore does not
remove the zeroing and does not broaden it. It only makes the same 0x200-byte
write range owner-valid by allocating the range first and restoring the stack
pointer immediately after.

## Fix

`Ldr_Inject_Entry32` now subtracts `0x200` from `ESP`, zeros from the new `ESP`,
and restores `ESP` before `ret`.

`Ldr_Inject_Entry64` now subtracts `0x200` from `RSP`, zeros from the new `RSP`,
and restores `RSP` before jumping to the original entrypoint address returned by
`Ldr_Inject_Entry`.

The zeroed byte range, entrypoint patch bytes, original-entrypoint restore path,
and F-Secure compatibility policy are unchanged.

## Acceptance Gate

`docs/plan/check-srev-094.py` validates the draft-07 schema, official references,
x86/x64 source shape, absence of below-stack `lea [esp/rsp-200h]` writes, stack
restore before `ret` / `jmp rdx`, local `ldr_init.c` injection topology, and
ledger entry. `docs/plan/check-srev-094.sh` is the matrix wrapper.

Runtime gate: Windows x86 and x64 process-launch matrix with normal process
entry, host injection, sandbox injection, F-Secure-compatible injected code,
third-party entrypoint hooks, and crash/unwind observation. Source gates prove
owner shape only; they do not prove third-party runtime compatibility.
