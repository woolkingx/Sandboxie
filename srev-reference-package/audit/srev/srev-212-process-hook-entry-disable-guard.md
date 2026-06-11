# SREV-212: Process Hook Entry Disable Guard

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/drv/process_hook.c` was the top unnamed reviewable core file
after SREV-211. It owns the local process/object/GUI hook-entry trampoline used
by XP-era kernel hook paths. `Process_BuildHookEntry` allocates a
`HOOK_TRAMP`, stamps `tramp->eyecatcher = tzuk`, writes a small machine-code
entry into `tramp->code`, and returns the address of that code. The code buffer
branches either to Sandboxie's replacement routine or to the original routine
depending on whether `Process_FindSandboxed*` finds sandbox state.

`Process_DisableHookEntry` is the unload-time inverse for those hook entries.
It rewrites bytes inside the generated entry so the test path always falls
through to the original system routine. Before this fix, it trusted any
non-local `HookEntry` value enough to derive a `HOOK_TRAMP` pointer and patch
bytes in the computed code stream.

## Data

`process_hook.c`, `process.h`, `Process_BuildHookEntry`,
`Process_DisableHookEntry`, `HOOK_TRAMP`, `HOOK_TRAMP_CODE_TO_TRAMP_HEAD`,
`tramp->eyecatcher`, `tramp->code[64]`, `tramp->target`,
`Process_FindSandboxed`, `Process_FindSandboxed64`, XP object parse hooks,
GUI XP hooks, and process notify fallback hooks.

## Official Shape

Microsoft documents `PsSetCreateProcessNotifyRoutine` and
`PsSetCreateProcessNotifyRoutineEx` as the supported process-notification
registration/removal APIs. Drivers must remove callbacks they register before
unload, and the Ex form waits for in-flight callbacks to complete when removing
a callback.

That official callback registration shape is already covered by SREV-100.
This SREV covers the local compatibility trampoline used by Sandboxie's XP-era
fallback paths when it cannot rely only on the supported callback list shape.
The trampoline's legal shape is therefore local: only code returned by
`Process_BuildHookEntry` is a valid input to `Process_DisableHookEntry`.

References:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-pssetcreateprocessnotifyroutine`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-pssetcreateprocessnotifyroutineex`

## Schema

`PROCESS_HOOK_ENTRY_DISABLE_GUARD` says:

- `process_hook.c` owns the generated hook-entry machine-code layout.
- `Process_BuildHookEntry` is the only creator for hook entries that
  `Process_DisableHookEntry` may rewrite.
- A generated hook entry is identified by `HOOK_TRAMP_CODE_TO_TRAMP_HEAD` and
  `tramp->eyecatcher == tzuk`.
- Disable logic must return without patching if the hook-entry value is null or
  does not identify a Sandboxie trampoline.
- The disable patch keeps the original schema: change `test eax,eax` to
  `xor eax,eax`, then hotpatch the entry prefix to jump to that modified test.

## Topology

```text
Process_BuildHookEntry
-> Hook_BuildTramp
-> HOOK_TRAMP header
-> eyecatcher = tzuk
-> generated entry code
-> XP object/GUI/process fallback hook pointer
```

Disable topology:

```text
hook pointer
-> HOOK_TRAMP_CODE_TO_TRAMP_HEAD
-> eyecatcher guard
-> generated code schema walk
-> test eax,eax becomes xor eax,eax
-> entry prefix becomes short jump to disabled test
```

## Logic Risk

`Process_DisableHookEntry` is a byte patcher. Without a local schema guard, a
stale, zero, or non-Sandboxie pointer reaching the unload path can make the
function compute a fake `HOOK_TRAMP` header and write into an arbitrary code
address. The normal callers track hook state, but the patch owner is still the
function that mutates the generated code stream.

## Fix

`Process_DisableHookEntry` now returns before patching when the entry is null
or when the computed trampoline header does not contain Sandboxie's `tzuk`
eyecatcher. Valid hook entries keep the existing disable behavior.

## Acceptance Gate

`docs/plan/check-srev-212.py` validates the draft-07 schema, official
references, `process.h` declaration coordinates, source-level trampoline
creator stamp, disable-time null/eyecatcher guard before byte patching, removal
of the stale unguarded disable shape, split ledger fragment, and the existing
XP object/GUI caller topology.

Runtime/build gate: Windows driver build plus XP-hook compatibility smoke on
supported legacy targets or a controlled test harness that creates a hook entry,
disables it, and verifies it routes to the original procedure. A negative test
should call the disable path with zero and a non-Sandboxie trampoline-shaped
address without mutating code.
