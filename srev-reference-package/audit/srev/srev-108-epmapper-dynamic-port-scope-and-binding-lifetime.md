# SREV-108: EpMapper Dynamic Port Scope And Binding Lifetime

## Data

`Sandboxie/core/svc/EpMapperServer.cpp` answers
`MSGID_EPMAPPER_GET_PORT_NAME` requests from sandboxed processes. It reads the
caller process id, maps that process to a sandbox box name, resolves an endpoint
by either configured service name or configured RPC interface id, and asks the
driver to open the discovered dynamic local-RPC endpoint.

The service-name path queries SCM for the service process id, then calls
`API_GET_DYNAMIC_PORT_FROM_PID` so the driver can find the owning `LRPC-*` ALPC
port under `\RPC Control`.

The interface-id path asks the local RPC endpoint mapper for elements matching a
configured `RPC_IF_ID`, converts each returned binding handle to a string
binding, accepts the first `ncalrpc:[LRPC-*]` endpoint, and stores it as
`\RPC Control\LRPC-*`.

On success the service builds driver-side `RpcPortFilter` message-id filters
and calls `API_OPEN_DYNAMIC_PORT` with process id `0`. The current driver API
schema contains only `port_name`, `process_id`, `port_id`, `filter_num`, and
`filter_ids`; it has no box name, sandbox id, session key, or scoped dynamic-port
identity field.

## Official Shape

Microsoft documents `RpcMgmtEpEltInqBegin` as creating an inquiry context for
viewing endpoint-map elements. Passing `NULL` as the endpoint binding views the
local host, `RPC_C_EP_MATCH_BY_IF` searches for elements containing the supplied
interface id, and `RPC_C_VERS_ALL` ignores version numbers for that interface.

Microsoft documents `RpcMgmtEpEltInqNextW` as returning one selected endpoint
map element. Returned elements are unordered. When `Binding` is non-NULL, the
RPC runtime allocates memory for the returned binding handle on each successful
call, and the application is responsible for freeing it with `RpcBindingFree`.

Microsoft documents `RpcBindingToStringBindingW` as converting a binding handle
to a string representation. Microsoft documents `RpcStringFreeW` as freeing RPC
strings allocated by RPC runtime routines. Microsoft documents
`RpcMgmtEpEltInqDone` as deleting the inquiry context and returning it as NULL.

Microsoft documents `QueryServiceStatusEx` with `SC_STATUS_PROCESS_INFO` as
returning a `SERVICE_STATUS_PROCESS` structure. That structure includes
`dwProcessId`, the service process id while the service is running.

Microsoft's public ALPC documentation is event/debugger shaped rather than a
driver-callable endpoint policy API. The ALPC ETW class documents send, receive,
wait-for-reply, wait-for-new-message, and stop-wait event types. The debugger
documentation says LPC is now emulated in ALPC and uses `!alpc` instead of the
old LPC extension. Therefore the per-process or per-sandbox ALPC filter in this
source file is a local driver policy/API schema problem, not a public Microsoft
API knob that the service can set with the existing call shape.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcmgmtepeltinqbegin
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcmgmtepeltinqnextw
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcmgmtepeltinqdone
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindingtostringbindingw
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindingfree
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcstringfreew
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-queryservicestatusex
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_status_process
https://learn.microsoft.com/en-us/windows/win32/etw/alpc
https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc
```

## Schema

Local schema:

```text
docs/plan/srev-108-epmapper-dynamic-port-scope-and-binding-lifetime.schema.json
```

The dynamic port scope and RPC binding lifetime contract is:

```text
caller process id maps to a sandbox box name before policy lookup
RpcPortBindingIfId resolves through local RPC endpoint mapper inquiry
RpcPortBindingSvc resolves through SCM service process id and driver ALPC owner lookup
each successful RpcMgmtEpEltInqNextW binding handle is freed with RpcBindingFree
RpcBindingToStringBindingW output is freed with RpcStringFreeW
RpcMgmtEpEltInqDone deletes the inquiry context after enumeration
API_OPEN_DYNAMIC_PORT currently carries process-id or global scope only
process id 0 is the existing global dynamic-port compatibility path
RpcPortFilter message ids are attached to the driver dynamic-port entry
per-sandbox dynamic ports require a driver/API schema extension with a scoped key
per-process or per-sandbox ALPC message filtering must not be pretended in service-only code
```

## Topology

Current endpoint resolution topology:

```text
PipeServer caller pid
  -> SbieApi_QueryProcess(pid) -> boxname
  -> request port id
       -> RpcPortBindingSvc -> OpenSCManager/OpenService/QueryServiceStatusEx
                              -> API_GET_DYNAMIC_PORT_FROM_PID
       -> RpcPortBindingIfId -> RpcMgmtEpEltInqBegin
                              -> RpcMgmtEpEltInqNextW
                              -> RpcBindingToStringBindingW
                              -> RpcStringFreeW
                              -> RpcBindingFree
                              -> RpcMgmtEpEltInqDone
  -> RpcPortFilter config in box
  -> API_OPEN_DYNAMIC_PORT(port, 0, port_id, filter_count, filter_ids)
  -> driver global dynamic-port list and filter
```

Current driver topology:

```text
API_OPEN_DYNAMIC_PORT_ARGS
  -> port_name
  -> process_id
  -> port_id
  -> filter_num
  -> filter_ids

Ipc_Api_OpenDynamicPort
  -> service process only
  -> copy fixed port name and id
  -> create or replace IPC_DYNAMIC_PORT in global Ipc_Dynamic_Ports by port_id
  -> copy filter ids into that entry
  -> if process_id != 0, additionally add the path to that process open_ipc_paths

Ipc_CheckPortRequest_Dynamic
  -> match requested object name against global dynamic-port entries
  -> parse local RPC message id from payload byte 20
  -> deny matching configured filter ids
```

The missing topology for the old TODO is a scoped key:

```text
box/process/session identity
  -> dynamic-port identity
  -> filter identity
  -> request-time match key
```

That key does not exist in the current `API_OPEN_DYNAMIC_PORT_ARGS` or
`IPC_DYNAMIC_PORT` shape, so a correct per-sandbox fix is a driver/API schema
change, not a service-only branch.

## Logic Risk

The old TODO correctly noticed that global dynamic ports are broad. But changing
the service call from process id `0` to the resolving process id would break the
documented local compatibility reason in the comment: some clients resolve the
dynamic endpoint in one sandboxed process and use it from another. The current
driver schema cannot express "global inside this sandbox only".

The concrete source bug found during the official-shape pass was different:
`RpcMgmtEpEltInqNextW` returns a binding handle allocated by the RPC runtime,
and the code converted it to a string but did not release the binding handle.
Repeated endpoint lookup could leak RPC binding resources in the service
process.

## Fix

The interface-id endpoint inquiry loop now frees every successfully returned
binding handle with `RpcBindingFree` after `RpcBindingToStringBindingW` and
`RpcStringFreeW`. The first accepted `LRPC-*` endpoint still stops enumeration,
and `RpcMgmtEpEltInqDone` still closes the inquiry context.

The stale TODO comments were replaced with a schema boundary comment: dynamic
RPC endpoints can be resolved by one sandboxed process and used by another;
`API_OPEN_DYNAMIC_PORT` currently exposes only process-id or global scope; and
per-process or per-sandbox ALPC message filtering requires a scoped
dynamic-port key in the driver/API schema.

No `RpcPortBindingIfId`, `RpcPortBindingSvc`, `RpcPortFilter`,
`Open[Name]Endpoint`, SCM lookup, driver dynamic-port list, or filter message-id
policy changed.

## Acceptance Gate

`docs/plan/check-srev-108.py` validates the draft-07 schema, official
references, endpoint mapper inquiry topology, RPC binding/string/inquiry
lifetime calls, source removal of stale per-sandbox/per-process TODO wording,
preservation of the global process-id `0` compatibility call, driver API schema
evidence that no sandbox key exists, dynamic-port filter topology, and ledger
entry. `docs/plan/check-srev-108.sh` is the matrix wrapper.

Runtime gate: Windows matrix with a configured `RpcPortBindingIfId`, configured
`RpcPortBindingSvc`, Chrome/Game Config Store style cross-process endpoint use,
`RpcPortFilter` allow/deny observations, repeated endpoint lookup under service
memory/resource tracing, sandboxed same-box cross-process access, different-box
negative case after any future scoped schema change, and ALPC ETW / debugger
observation for the actual local-RPC send/receive path.
