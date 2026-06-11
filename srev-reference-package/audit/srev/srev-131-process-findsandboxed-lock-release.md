# SREV-131: Process FindSandboxed Lock Release

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/process.h`, `Sandboxie/core/drv/process.c`, Microsoft ERESOURCE and IRQL references |
| Output artifact | `docs/plan/srev-131-process-findsandboxed-lock-release.schema.json`, `docs/plan/check-srev-131.py`, `docs/plan/check-srev-131.sh`, ledger row |
| Owner | `Process_Find`, `Process_FindSandboxed`, and `Process_ListLock` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows driver runtime remains required |

## Evidence

`Sandboxie/core/drv/process.h` was the highest-ranked unnamed reviewable core file after SREV-130. Its public process lookup contract says `Process_Find` can return `PROCESS_TERMINATED`, and the surrounding comments expose lock-sensitive process state transitions. `Sandboxie/core/drv/process.c` implements that contract by raising IRQL to `APC_LEVEL`, acquiring `Process_ListLock`, and either releasing it locally when `out_irql` is null or transferring the locked state to the caller by writing the old IRQL through `out_irql`.

`Process_FindSandboxed` wraps `Process_Find` and hides host-injection process records by returning `NULL` when `proc->bHostInject` is set. Before this SREV, that wrapper returned `NULL` without releasing the lock and restoring IRQL when the caller supplied `out_irql`. That made the wrapper's filtered `NULL` path different from a direct `Process_Find` miss: the caller received no `PROCESS *` to inspect, but the kernel lock/IRQL state could remain transferred.

Microsoft documents `ExAcquireResourceSharedLite` as acquiring a resource for shared access and says the caller can release it with `ExReleaseResourceLite`. Microsoft documents `ExReleaseResourceLite` as releasing an executive resource owned by the current thread. Microsoft documents `KeRaiseIrql` as storing the original IRQL for later `KeLowerIrql`, and says callers should restore the original IRQL as soon as possible. Microsoft documents `KeLowerIrql` as restoring the IRQL to the value returned by the immediately preceding raise call.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourcesharedlite
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exreleaseresourcelite
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-keraiseirql
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kelowerirql

## Data

`Process_Find`, `Process_FindSandboxed`, `Process_ListLock`, `Process_Map`, `PROCESS`, `PROCESS_TERMINATED`, `out_irql`, `KIRQL irql`, `KeRaiseIrql`, `KeLowerIrql`, `ExAcquireResourceSharedLite`, `ExReleaseResourceLite`, and `proc->bHostInject`.

## Schema

`PROCESS_FINDSANDBOXED_LOCK_RELEASE` says:

- `Process_Find` owns the `Process_ListLock` and raised-IRQL transfer contract when `out_irql` is non-null.
- `Process_Find` raises to `APC_LEVEL` and acquires `Process_ListLock` before returning a protected `PROCESS *`.
- `Process_Find` without `out_irql` releases `Process_ListLock` and lowers IRQL before return.
- `Process_Find` with `out_irql` stores the old IRQL for the caller and leaves `Process_ListLock` held.
- `Process_FindSandboxed` may filter a found `PROCESS` when `bHostInject` is set.
- `Process_FindSandboxed` returning `NULL` after `bHostInject` filtering releases `Process_ListLock` when `out_irql` is non-null.
- `Process_FindSandboxed` returning `NULL` after `bHostInject` filtering lowers IRQL using the old IRQL from `out_irql`.
- `Process_FindSandboxed` does not release `Process_ListLock` for `NULL` returned directly by `Process_Find`.
- `Process_FindSandboxed` preserves `PROCESS_TERMINATED` sentinel behavior.
- `Process_FindSandboxed` leaves successful sandboxed `PROCESS` ownership and caller-release topology unchanged.

## Topology

The legal `Process_Find` transfer topology is:

```text
Process_Find(..., &irql)
  -> KeRaiseIrql(APC_LEVEL, &local_irql)
  -> ExAcquireResourceSharedLite(Process_ListLock, TRUE)
  -> proc found
  -> *out_irql = local_irql
  -> caller owns release/lower edge while using proc
```

The corrected `Process_FindSandboxed` host-inject filter topology is:

```text
Process_FindSandboxed(..., &irql)
  -> Process_Find transfers Process_ListLock and old IRQL
  -> proc exists and is not PROCESS_TERMINATED
  -> proc->bHostInject
  -> ExReleaseResourceLite(Process_ListLock)
  -> KeLowerIrql(irql)
  -> return NULL
```

Direct miss and sentinel topology remain separate:

```text
Process_Find returns NULL
  -> Process_FindSandboxed returns NULL without an extra release

Process_Find returns PROCESS_TERMINATED
  -> Process_FindSandboxed returns PROCESS_TERMINATED unchanged
```

## Logic Risk

The wrapper changed the semantic value from "found protected process" to "no sandboxed process" while still inheriting the lower-level lock transfer. That is a topology mismatch: a caller cannot safely release a lock around a `NULL` process unless the API contract says every `NULL` can still carry lock ownership. `Process_Find` already treats direct misses as no protected process state, and `Process_FindSandboxed` should preserve that shape after filtering host-injection records.

The minimal owner-local repair is to release `Process_ListLock` and lower IRQL only on the filtered `bHostInject` path where `Process_Find` actually returned a protected `PROCESS *` and `out_irql` asked to transfer lock state. It does not change process lookup policy, sandbox membership policy, or the `PROCESS_TERMINATED` sentinel.

## Fix

`Process_FindSandboxed` now checks `if (out_irql)` inside the `proc->bHostInject` filter branch, then calls `ExReleaseResourceLite(Process_ListLock)` and `KeLowerIrql(*out_irql)` before setting `proc = NULL`. Successful sandboxed process returns and `PROCESS_TERMINATED` returns keep the existing caller-owned release contract.

## Acceptance Gate

`docs/plan/check-srev-131.py` validates the draft-07 schema, official references, `Process_Find` lock/IRQL transfer shape, `Process_FindSandboxed` host-inject filter shape, release/lower ordering before `proc = NULL`, preservation of direct miss and `PROCESS_TERMINATED` topology, stale filtered-NULL-without-release shape removal, header declaration, and ledger entry. `docs/plan/check-srev-131.sh` is the matrix wrapper.

Runtime/build gate: Windows driver build with `XP_SUPPORT` enabled for `process.c`, normal sandboxed lookup proving caller-owned release remains intact, `bHostInject` filtered lookup proving `NULL` return does not leak `Process_ListLock` or raised IRQL, `PROCESS_TERMINATED` lookup proving sentinel behavior is unchanged, and Driver Verifier or kernel debugger observation proving no leaked ERESOURCE ownership.
