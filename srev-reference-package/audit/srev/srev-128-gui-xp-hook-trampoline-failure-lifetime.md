# SREV-128: GUI XP Hook Trampoline Failure Lifetime

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/gui_xp.c`, `Sandboxie/core/dll/hook_tramp.c`, Microsoft pool allocation/free DDI references |
| Output artifact | `docs/plan/srev-128-gui-xp-hook-trampoline-failure-lifetime.schema.json`, `docs/plan/check-srev-128.py`, `docs/plan/check-srev-128.sh`, ledger row |
| Owner | `Gui_HookService` in `Sandboxie/core/drv/gui_xp.c` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows XP hook runtime remains required |

## Evidence

`Sandboxie/core/drv/gui_xp.c` was the highest-ranked unnamed reviewable core file after SREV-127. `Gui_HookService` builds a trampoline for a kernel service, optionally patches a special SpySweeper push-jump trampoline, publishes the trampoline through `*pSourceFunc`, builds a jump stub, then modifies kernel code under MDL/DPC freeze control.

The old failure topology had two invalid lifetime edges:

1. `Trampoline = Hook_BuildTramp(...)` was followed by the `push_jmp_target` patch block before `if (! Trampoline)`. `Hook_BuildTramp` in `Sandboxie/core/dll/hook_tramp.c` can return `NULL` when instruction counting fails, trampoline allocation fails, or trampoline copy fails.
2. The `finish` block freed `context` with `ExFreePoolWithTag(context, tzuk)` and then the failure block restored `*pSourceFunc = context->SaveBytesAddr;`.

Microsoft documents `ExAllocatePoolWithTag` as returning `NULL` when insufficient pool memory exists, and its pool documentation also says drivers must access only storage they explicitly allocated. Microsoft documents `ExFreePool` as releasing pool memory and says the memory block must not be accessed after it is freed. The same remarks point drivers to `ExFreePoolWithTag` for buffers allocated by `ExAllocatePoolWithTag`.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepoolwithtag
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exfreepool

## Data

`Gui_HookService`, `pSourceFunc`, `OriginalSourceFunc`, `pJumpStub`, `TargetFunc`, `GUI_HOOKSERVICE_CONTEXT`, `SaveBytesAddr`, `Trampoline`, `Hook_BuildTramp`, `push_jmp_target`, `Hook_BuildJump`, `Process_BuildHookEntry`, `Gui_HookFreeze`, `ExFreePoolWithTag`, and `STATUS_UNSUCCESSFUL`.

## Schema

`GUI_XP_HOOK_TRAMPOLINE_FAILURE_LIFETIME` says:

- `Gui_HookService` stores the original source function pointer in owner-local storage before any failure edge can free the hook context.
- `GUI_HOOKSERVICE_CONTEXT::SaveBytesAddr` mirrors the original source function pointer but is not the failure-restore owner after context cleanup.
- `Hook_BuildTramp` may return `NULL` when instruction analysis or trampoline allocation/copy fails.
- `Gui_HookService` checks the `Hook_BuildTramp` result before SpySweeper push-jump trampoline writes through it.
- `push_jmp_target` special trampoline patching only runs after `Trampoline` is non-null.
- Failure cleanup frees `GUI_HOOKSERVICE_CONTEXT` only before restoring `pSourceFunc` from `OriginalSourceFunc`.
- Failure cleanup never dereferences `context` after `ExFreePoolWithTag(context, tzuk)`.
- Successful hook topology and `Process_BuildHookEntry` behavior are unchanged.
- XP win32k service discovery, hotfix prolog handling, MDL locking, and DPC freeze topology are unchanged.

## Topology

The successful path remains:

```text
pSourceFunc original -> SaveBytesAddr snapshot -> prolog analysis -> Hook_BuildTramp -> optional push-jump patch -> *pSourceFunc trampoline -> Process_BuildHookEntry -> MDL writable mapping -> DPC freeze -> Hook_BuildJump
```

The corrected failure path is:

```text
OriginalSourceFunc snapshot -> context allocation/init -> any failure -> freeze/thread cleanup -> ExFreePoolWithTag(context) -> *pJumpStub = 0 -> *pSourceFunc = OriginalSourceFunc -> FALSE
```

The failure restore owner is now the local `OriginalSourceFunc`, not a field inside freed `context`.

## Logic Risk

Kernel hook installation is a state machine over executable pointers. A trampoline pointer becomes legal only after `Hook_BuildTramp` returns non-null. The previous ordering let the SpySweeper special-case write bytes through `Trampoline` before that legality gate. On allocation or decode failure this could become a NULL write in kernel context.

The second edge is a lifetime bug: `context->SaveBytesAddr` contains the right value, but `context` no longer owns readable storage after `ExFreePoolWithTag(context, tzuk)`. The correct local repair is to snapshot the original source pointer into a stack variable before context cleanup and restore from that variable after cleanup.

## Fix

`Gui_HookService` now captures `OriginalSourceFunc = *pSourceFunc` before allocating the context. `context->SaveBytesAddr` is initialized from that snapshot. The `Hook_BuildTramp` result is checked immediately; the SpySweeper push-jump patch runs only after `Trampoline` is known non-null. On failure, `*pSourceFunc` is restored from `OriginalSourceFunc` instead of `context->SaveBytesAddr` after `context` has been freed.

No service discovery, hotfix prolog detection, trampoline construction policy, hook entry generation, MDL locking, DPC freeze, successful jump write, or retry topology changed.

## Acceptance Gate

`docs/plan/check-srev-128.py` validates the draft-07 schema, official references, local `Hook_BuildTramp` NULL-return shape, original source pointer snapshot, immediate trampoline null gate before `push_jmp_target`, stale post-free `context->SaveBytesAddr` restore removal, unchanged successful hook topology, and ledger entry. `docs/plan/check-srev-128.sh` is the matrix wrapper.

Runtime/build gate: Windows build for `gui_xp.c`, XP hook install smoke for all affected services, failure injection where `Hook_BuildTramp` returns `NULL` on a `push_jmp_target` prolog proving no NULL write and clean `FALSE` return, failure injection after `*pSourceFunc = Trampoline` proving restore to original pointer, and Driver Verifier or kernel debugger observation proving no freed context access.
