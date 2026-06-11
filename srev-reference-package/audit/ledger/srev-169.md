---
kind: srev-ledger-entry
id: SREV-169
title: IPC Unload List Resources
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/drv/ipc.h
spec: docs/plan/srev-169-ipc-unload-list-resources.md
schema: docs/plan/srev-169-ipc-unload-list-resources.schema.json
checker: docs/plan/check-srev-169.py
runtime_gate: "Windows driver build, driver load/unload smoke after dynamic RPC port registration, driver load/unload smoke after IPC directory creation, and Driver Verifier or pool tracking proof"
---

### SREV-169: IPC Unload List Resources

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft driver unload and ERESOURCE documentation review; needs Windows driver unload/runtime proof |
| Evidence | `Sandboxie/core/drv/ipc.h` was the top unnamed reviewable core file after SREV-168. It defines the global `IPC_DYNAMIC_PORTS` list owner. `Sandboxie/core/drv/ipc_port.c` allocates `IPC_DYNAMIC_PORT` nodes with `Mem_AllocEx` and inserts them into `Ipc_Dynamic_Ports.Ports`. `Sandboxie/core/drv/ipc.c` allocates `DIR_OBJ_HANDLE` nodes for saved IPC directory handles. Before this SREV, `Ipc_Unload` freed `Ipc_Dynamic_Ports.pPortLock` and closed `Ipc_ObjDirs` handles, but did not remove/free the dynamic-port or directory-handle list nodes. |
| Data | `Sandboxie/core/drv/ipc.h`, `Sandboxie/core/drv/ipc.c`, `Sandboxie/core/drv/ipc_port.c`, `IPC_DYNAMIC_PORT`, `IPC_DYNAMIC_PORTS`, `Ipc_Dynamic_Ports`, `Ipc_Dynamic_Ports.Ports`, `Ipc_Dynamic_Ports.pPortLock`, `Ipc_Dynamic_Ports.pSpoolerPort`, `Ipc_Api_OpenDynamicPort`, `Ipc_CreateDynamicPort`, `Ipc_Unload`, `DIR_OBJ_HANDLE`, `Ipc_ObjDirs`, `Ipc_DirLock`, `List_Remove`, `Mem_Free`, `Mem_FreeLockResource`, `ExAcquireResourceExclusiveLite`, `ExReleaseResourceLite`, `KeEnterCriticalRegion`, and `KeLeaveCriticalRegion`. |
| Schema | `IPC_UNLOAD_LIST_RESOURCES` says `ipc.h` owns the dynamic-port data shape; dynamic ports may be allocated and inserted under `pPortLock`; `Ipc_Unload` must drain and free dynamic-port nodes before freeing `pPortLock`; `pSpoolerPort` must be cleared after draining the list; and `Ipc_Unload` must close every saved IPC directory handle, remove every `DIR_OBJ_HANDLE`, and free every node before freeing `Ipc_DirLock`. |
| Topology | Legal flow is `Ipc_Init` -> initialize list and lock resources -> dynamic port / directory handle allocation -> list insertion under the owner lock -> `Ipc_Unload` acquires the list owner lock -> remove and free nodes -> release and free lock resources. |
| Logic Risk | The old unload path leaked kernel pool allocations for every dynamic IPC port and every saved IPC directory-handle node. It also freed the dynamic-port lock without first draining the list, so the data nodes outlived the owner edge that makes safe list mutation explicit. |
| Official Shape | `docs/plan/srev-169-ipc-unload-list-resources.md` records Microsoft driver unload, driver-allocated resource, `ExAcquireResourceExclusiveLite`, and `ExReleaseResourceLite` references. `docs/plan/srev-169-ipc-unload-list-resources.schema.json` records the JSON Schema draft-07 local `IPC_UNLOAD_LIST_RESOURCES` contract. |
| Fix | `Ipc_Unload` now drains `Ipc_Dynamic_Ports.Ports` under exclusive `pPortLock`, frees each `IPC_DYNAMIC_PORT` using its variable-tail allocation size, clears `pSpoolerPort`, releases the lock, and then frees the lock resource. It also drains `Ipc_ObjDirs` by saving the next pointer, closing the saved handle, removing the node, freeing `DIR_OBJ_HANDLE`, and then moving to the saved next node before freeing `Ipc_DirLock`. |
| Acceptance Gate | `docs/plan/check-srev-169.py` validates the draft-07 schema, official references, `ipc.h` dynamic-port owner shape, `ipc_port.c` allocation/replacement shape, `Ipc_Unload` dynamic-port drain, directory-handle node free, and ledger entry; `docs/plan/check-srev-169.sh` is the matrix wrapper. Runtime/build gate: Windows driver build; driver load/unload smoke after dynamic RPC port registration; driver load/unload smoke after IPC directory creation; Driver Verifier or pool tracking proof that dynamic-port and directory-handle allocations are released. |
