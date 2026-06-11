# SREV-112 ComServer Slave IPC Open Lifetime

## Data

Owner file:

```text
Sandboxie/core/svc/comserver.cpp
```

Reviewed nodes:

```text
ComServer::RunSlave
Global\\<sandboxie>_ComProxy...
OpenMutex
OpenEvent(Event1)
OpenEvent(Event2)
OpenFileMapping
MapViewOfFile
CoInitializeEx
CoInitializeSecurity
SetEvent(Event2)
```

## Schema

`COMSERVER_SLAVE_IPC_OPEN_LIFETIME` defines these local contracts:

- `RunSlave` accepts only the bounded parent-generated proxy command line.
- The proxy command line must contain the colon separator before object-name
  suffix replacement.
- The slave opens the parent-created mutex, request event, reply event, and
  file mapping by name in the Global namespace.
- Each opened kernel handle is owned by the slave process and must be closed on
  startup failure.
- Each mapped view returned by `MapViewOfFile` is owned by the slave process and
  must be unmapped on startup failure.
- `Event1` is the request event waited by the slave.
- `Event2` is the reply event signaled by the slave after writing `pMap`.
- `CoInitializeEx` must succeed before COM library calls are used by the slave.
- Successful `CoInitializeEx` must be balanced by `CoUninitialize` on the local
  cleanup path.
- The steady-state success path still exits through the existing parent-death
  `ExitProcess` behavior.

## Topology

Parent service side:

```text
LockSlave
  -> CreateMutex(name: ...Mutex)
  -> CreateEvent(name: ...Event1)
  -> CreateEvent(name: ...Event2)
  -> CreateFileMapping(name: ...Map)
  -> CreateProcessAsUser(SbieSvc.exe <same proxy command line>)
```

Slave side:

```text
RunSlave(cmdline)
  -> validate cmdline length and colon separator
  -> OpenMutex(...Mutex)
  -> OpenEvent(...Event1)
  -> OpenEvent(...Event2)
  -> OpenFileMapping(...Map)
  -> MapViewOfFile
  -> HeapCreate
  -> CoInitializeEx(COINIT_APARTMENTTHREADED)
  -> CoInitializeSecurity(existing compatibility settings)
  -> WaitForMultipleObjects(parent mutex, Event1)
  -> dispatch COM request through pMap
  -> SetEvent(Event2)
```

## Logic Risk

The previous source opened `Event2` but then checked `hEvent1` again. If the
reply event open failed while `Event1` succeeded, the slave continued with a
NULL `hEvent2` and later called `SetEvent(hEvent2)`. The parent waits on the
reply event, so this can turn a startup/open failure into a COM proxy hang.

The same startup block returned early after opening handles and mapping a view.
The process normally exits shortly after `RunSlave` returns, but the local owner
contract is still clear: each successful open or map has a paired cleanup edge.

The command-line colon is also part of the data shape. Without it, suffix
replacement writes through a null pointer.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-openeventw
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-openfilemappingw
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile
- https://learn.microsoft.com/en-us/windows/win32/memory/closing-a-file-mapping-object
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-unmapviewoffile
- https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coinitializeex
- https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coinitializesecurity
- https://learn.microsoft.com/en-us/windows/win32/sync/mutex-objects

## Fix

`RunSlave` now:

- rejects a malformed proxy command line without a colon separator;
- checks `hEvent2` after opening `Event2`;
- routes startup failures through one local cleanup block;
- closes opened mutex/event/file-mapping handles on startup failure;
- unmaps the mapped file view on startup failure;
- checks `CoInitializeEx` before entering the COM request loop;
- calls `CoUninitialize` on the local cleanup path after successful
  `CoInitializeEx`.

The COM request protocol, object names, access masks, parent process creation,
`CoInitializeSecurity` compatibility arguments, request dispatch, and parent
death `ExitProcess` behavior are unchanged.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-112.py
bash docs/plan/check-srev-112.sh
```

Runtime gate still required:

- Windows COM proxy startup with normal Event1/Event2/Map objects.
- Negative startup matrix where Mutex, Event1, Event2, or Map open fails.
- Parent wait observation proving `Event2` is signaled after successful request
  dispatch.
- COM apartment initialization failure injection.
- Resource observation for mapped view and handle cleanup on startup failure.
