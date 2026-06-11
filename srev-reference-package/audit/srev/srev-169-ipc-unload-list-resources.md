# SREV-169: IPC Unload List Resources

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/drv/ipc.h, ipc.c, ipc_port.c, and Microsoft driver unload / ERESOURCE documentation
output artifact: IPC unload releases dynamic-port and directory-handle list allocations before freeing their locks
owner: Sandboxie/core/drv/ipc.h
acceptance gate: docs/plan/check-srev-169.py and docs/plan/check-srev-169.sh
```

## Data

`ipc.h` defines the global dynamic IPC port state:

```c
typedef struct _IPC_DYNAMIC_PORT {
    LIST_ELEM list_elem;
    WCHAR wstrPortId[DYNAMIC_PORT_ID_CHARS];
    WCHAR wstrPortName[DYNAMIC_PORT_NAME_CHARS];
    ULONG FilterCount;
    UCHAR FilterIDs[0];
} IPC_DYNAMIC_PORT;

typedef struct _IPC_DYNAMIC_PORTS {
    PERESOURCE pPortLock;
    LIST Ports;
    IPC_DYNAMIC_PORT *pSpoolerPort;
} IPC_DYNAMIC_PORTS;
```

`ipc_port.c` allocates `IPC_DYNAMIC_PORT` nodes with `Mem_AllocEx` and inserts
them into `Ipc_Dynamic_Ports.Ports`. `ipc.c` also allocates `DIR_OBJ_HANDLE`
nodes for directory handles kept in `Ipc_ObjDirs`. Before this SREV,
`Ipc_Unload` freed `Ipc_Dynamic_Ports.pPortLock` and closed `Ipc_ObjDirs`
handles, but it did not free the dynamic-port list nodes or the directory-handle
list nodes.

## Official Shape

- Microsoft documents that a non-PnP driver's unload routine must release
  driver-allocated resources and undo work performed by `DriverEntry` /
  reinitialize routines:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/unload-routine-functionality`.
- Microsoft's driver-allocated resource guidance says unload must ensure no
  other driver routine is using a resource before releasing it and must release
  driver-allocated pool resources:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/releasing-driver-allocated-resources`.
- Microsoft documents `ExAcquireResourceExclusiveLite` as the exclusive access
  primitive for an `ERESOURCE`; normal kernel APC delivery must be disabled
  with `KeEnterCriticalRegion` until the resource is released:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourceexclusivelite`.
- Microsoft documents `ExReleaseResourceLite` as releasing the executive
  resource owned by the current thread:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exreleaseresourcelite`.

## Schema

`IPC_UNLOAD_LIST_RESOURCES` says:

- `ipc.h` owns the `IPC_DYNAMIC_PORT` / `IPC_DYNAMIC_PORTS` data shape.
- `ipc_port.c` may allocate dynamic-port nodes and insert them under
  `Ipc_Dynamic_Ports.pPortLock`.
- `ipc.c` owns `Ipc_Unload` and must free list nodes it owns before freeing the
  corresponding lock resource.
- Dynamic-port unload must acquire `pPortLock` exclusively inside a critical
  region, remove every node from `Ipc_Dynamic_Ports.Ports`, free the node with
  its variable-tail size, clear `pSpoolerPort`, release the lock, leave the
  critical region, and only then free the lock resource.
- Directory-handle unload must close every saved handle, remove every
  `DIR_OBJ_HANDLE` from `Ipc_ObjDirs`, and free every node before freeing
  `Ipc_DirLock`.
- Linux source gates are not Windows driver unload / Driver Verifier proof.

## Topology

Legal resource lifetime:

```text
Ipc_Init
  -> initialize Ipc_Dynamic_Ports.Ports and pPortLock
  -> Ipc_Api_OpenDynamicPort allocates IPC_DYNAMIC_PORT nodes
  -> Ipc_CreateBoxPath / Ipc_Api_CreateDirOrLink allocate DIR_OBJ_HANDLE nodes
  -> Ipc_Unload acquires list owner lock
  -> remove + free nodes
  -> free lock resources
```

The lock is the topology owner for list mutation. The unload routine must not
free the lock first and then lose the only safe mutation edge for the list.

## Logic Risk

The old unload path leaked kernel pool allocations for every dynamic IPC port
and every saved IPC directory-handle node. In normal long-lived service use this
is mostly a driver unload / update path defect, but it is still the wrong
resource lifecycle: the data nodes outlive their owner lock and the directory
handle node storage outlives the handle close.

## Fix

`Ipc_Unload` now drains `Ipc_Dynamic_Ports.Ports` under exclusive `pPortLock`,
frees each `IPC_DYNAMIC_PORT` with the variable-tail allocation size, clears
`pSpoolerPort`, releases the lock, and then frees the lock resource.

It also drains `Ipc_ObjDirs` by saving the next pointer, closing each saved
handle, removing the list node, freeing the `DIR_OBJ_HANDLE`, and moving to the
saved next node before `Ipc_DirLock` is freed.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-169.py
bash docs/plan/check-srev-169.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-169.py &&
bash docs/plan/check-srev-169.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows driver build; driver load/unload smoke after
dynamic RPC port registration; driver load/unload smoke after IPC directory
creation; Driver Verifier or pool tracking proof that dynamic-port and
directory-handle allocations are released.
