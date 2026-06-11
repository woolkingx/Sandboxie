# SREV-070: Handle Close Handler Lifetime

## Data

`Sandboxie/core/dll/handle.c` owns per-handle state and a list of close
handlers. `Handle_RegisterHandler` allocates one `HANDLE_HANDLER` node per
registered close callback. `Handle_UnRegisterHandler` removes a matching node
before the handle is closed, optionally returning the stored callback parameter
through `void **pParams`.

The relevant data nodes are:

```text
HANDLE_STATE CloseHandlers list
HANDLE_HANDLER allocation
HANDLE_HANDLER Param
Handle_UnRegisterHandler pParams output slot
List_Remove ownership transition
Dll_Free ownership release
```

## Local Shape

The local header defines the unregister boundary as:

```text
VOID Handle_UnRegisterHandler(HANDLE FileHandle, P_HandlerFunc CloseHandler, void** pParams);
```

That means `pParams` is an optional caller-owned output slot for the stored
`Param` pointer. The allocated `HANDLE_HANDLER` node is owned by the handle
module until it is either executed by `Handle_ExecuteCloseHandler` or explicitly
unregistered.

## Schema

Local schema:

```text
docs/plan/srev-070-handle-close-handler-lifetime.schema.json
```

The close-handler list contract is:

```text
Register may insert a node only after Dll_Alloc succeeds.
Unregister writes the stored Param through *pParams when pParams is non-null.
Unregister transfers the node out of the list and then frees it.
Execute-close transfers all remaining nodes out of the list and frees them.
```

## Topology

```text
RegisterHandler -> HANDLE_STATE.CloseHandlers -> UnRegisterHandler or ExecuteCloseHandler
```

`handle.c` owns the close-handler node lifecycle. Callers own only the callback
function and optional param pointer value; they do not own the node allocation.

## Logic Risk

Before this patch, `Handle_RegisterHandler` dereferenced the newly allocated
handler node without checking allocation success. `Handle_UnRegisterHandler`
assigned `pParams = handler->Param`, which changed only the local pointer
variable and did not write back to the caller's output slot. It also removed the
handler from the list without freeing the node, leaking the allocation for every
explicit unregister path.

## Fix

`Handle_RegisterHandler` now leaves the critical section and returns `FALSE` if
`Dll_Alloc(sizeof(HANDLE_HANDLER))` fails. `Handle_UnRegisterHandler` now writes
`*pParams = handler->Param` when an output slot is supplied, removes the node
from the list, and releases the node with `Dll_Free(handler)`.

## Acceptance Gate

`docs/plan/check-srev-070.py` validates the draft-07 schema, local header
boundary, register allocation gate, unregister output-slot write, node removal,
node free, and ledger entry.

Windows gate: explicit key/file/IPC merge unregister paths do not leak handler
nodes; future callers that request `pParams` receive the stored parameter;
allocation failure does not dereference a null handler node.
