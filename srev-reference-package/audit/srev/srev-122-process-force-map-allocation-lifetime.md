# SREV-122 Process Force Map Allocation Lifetime

## Data

Owner file:

```text
Sandboxie/core/drv/process_force.c
```

Reviewed nodes:

```text
Process_DfpInsert
Process_FcpInsert
Process_DfpDelete
Process_FcpDelete
Process_MapDfp
Process_MapFcp
FORCE_PROCESS_2
FORCE_PROCESS_3
Mem_Alloc
map_insert
Process_ListLock
KeRaiseIrql
KeLowerIrql
ExAcquireResourceExclusiveLite
ExReleaseResourceLite
```

## Schema

`PROCESS_FORCE_MAP_ALLOCATION_LIFETIME` defines these local contracts:

- `Mem_Alloc` may return `NULL` because the underlying pool allocation can
  fail.
- `Process_DfpInsert(PROCESS_TERMINATED, ProcessId)` owns the DFP record
  allocation while it holds `Process_ListLock`; if allocation fails it releases
  `Process_ListLock`, restores the previous IRQL, and returns `FALSE`.
- `Process_DfpInsert(ParentId, ProcessId)` is called while the process list is
  already locked; if child DFP record allocation fails it returns `FALSE`
  without inserting a null or partially initialized map record.
- `Process_FcpInsert` owns the FCP record allocation while it holds
  `Process_ListLock`; if allocation fails it releases `Process_ListLock`,
  restores the previous IRQL, and returns without inserting a map record.
- DFP/FCP delete, check, map key, silent flag, box-name copy, and force-policy
  semantics are unchanged.

## Topology

```text
Session_Api_DisableForce
  -> Process_DfpInsert(PROCESS_TERMINATED, ProcessId)
      -> raise IRQL
      -> acquire Process_ListLock
      -> delete old Process_MapDfp record
      -> allocate FORCE_PROCESS_2
      -> map_insert or fail closed
      -> release Process_ListLock
      -> restore IRQL

Process_NotifyProcess_Create
  -> Process_DfpInsert(ParentId, ProcessId)
      -> caller already owns process-list lock
      -> delete old child Process_MapDfp record
      -> allocate FORCE_PROCESS_2 only when parent is in Process_MapDfp
      -> map_insert or return FALSE

Session_Api_ForceChildren
  -> Process_FcpInsert(ProcessId, boxname)
      -> raise IRQL
      -> acquire Process_ListLock
      -> delete old Process_MapFcp record
      -> allocate FORCE_PROCESS_3
      -> map_insert or fail closed
      -> release Process_ListLock
      -> restore IRQL
```

## Logic Risk

The old DFP/FCP insertion paths allocated map records and immediately wrote
`proc->pid`, `proc->silent`, or `proc->boxname`. A failed pool allocation would
therefore become a kernel null dereference while the force-process map lock was
held.

The correct local repair is an allocation lifetime gate at the map-record owner
boundary. It does not change which processes are force-disabled, which child
processes inherit a forced box, how DFP/FCP records are keyed, or how checks
read those maps.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepoolwithtag
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourceexclusivelite
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exreleaseresourcelite
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-keraiseirql
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kelowerirql

## Fix

`Process_DfpInsert(PROCESS_TERMINATED, ProcessId)` now checks the
`FORCE_PROCESS_2` allocation before writing fields or inserting into
`Process_MapDfp`; on failure it releases `Process_ListLock`, lowers IRQL, and
returns `FALSE`.

`Process_DfpInsert(ParentId, ProcessId)` now checks the child
`FORCE_PROCESS_2` allocation before writing fields or inserting into
`Process_MapDfp`; on failure it returns `FALSE` to the already-locked caller.

`Process_FcpInsert` now checks the `FORCE_PROCESS_3` allocation before writing
fields or inserting into `Process_MapFcp`; on failure it releases
`Process_ListLock`, lowers IRQL, and returns.

No DFP/FCP map key, delete path, check path, silent flag behavior, box-name copy
shape, force-alert policy, force-children policy, or process-list lock ownership
changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-122.py
bash docs/plan/check-srev-122.sh
```

Runtime/build gate still required:

- Windows driver build for `process_force.c`.
- Pool-allocation failure injection for
  `Process_DfpInsert(PROCESS_TERMINATED, ProcessId)` proving no null
  dereference and balanced `Process_ListLock` / IRQL release.
- Pool-allocation failure injection for
  `Process_DfpInsert(ParentId, ProcessId)` proving no null map insert while the
  caller-owned lock remains owned by the caller.
- Pool-allocation failure injection for `Process_FcpInsert` proving no null
  dereference and balanced `Process_ListLock` / IRQL release.
- Positive DFP/FCP smoke proving unchanged insert, check, delete, silent flag,
  and box-name propagation behavior.
