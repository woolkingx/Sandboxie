# SREV-229: EpMapper Server Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-228, `Sandboxie/core/svc/EpMapperServer.h` was the top unnamed
reviewable core file. Source readback shows it is a declaration-only service
header: it includes `PipeServer.h`, declares `class EpMapperServer`, exposes a
constructor that receives `PipeServer *`, and declares the static PipeServer
handler plus the private `EpmapperGetPortNameHandler` implementation entry.

The runtime and wire owners are not this header:

- `Sandboxie/core/svc/EpMapperServer.cpp` registers `MSGID_EPMAPPER` with
  `PipeServer` and owns the endpoint-resolution logic.
- `Sandboxie/core/svc/EpMapperWire.h` owns the fixed request/reply wire fields.
- `Sandboxie/core/dll/rpcrt.c` owns the DLL-side producer/cache of dynamic local
  RPC endpoint requests.
- `Sandboxie/core/drv/ipc_port.c` owns the driver dynamic-port table and filter
  attachment.

SREV-108 already owns the dynamic-port scope and RPC binding lifetime risk in
`EpMapperServer.cpp`. SREV-218 already owns the fixed wire string and
`ncalrpc:[endpoint]` parsing contract across `EpMapperWire.h`,
`EpMapperServer.cpp`, `rpcrt.c`, and `ipc_port.c`.

## Data

`EpMapperServer`, `PipeServer`, `MSG_HEADER`, `Handler`,
`EpmapperGetPortNameHandler`, `MSGID_EPMAPPER`, `MSGID_EPMAPPER_GET_PORT_NAME`,
`EPMAPPER_GET_PORT_NAME_REQ`, `EPMAPPER_GET_PORT_NAME_RPL`,
`EpMapperServer.cpp`, `EpMapperWire.h`, `rpcrt.c`, and `ipc_port.c`.

## Schema

`EPMAPPER_SERVER_HEADER_TOPOLOGY_CONTRACT` says:

- `EpMapperServer.h` is a declaration-only service header.
- The header may declare the service class, constructor, static PipeServer
  handler, and concrete request handler entry point.
- The header must not be treated as the owner of RPC endpoint parsing, fixed
  wire string validation, dynamic-port policy, service control manager lookup,
  RPC runtime binding lifetime, or driver dynamic-port storage.
- Runtime behavior changes belong to the owner that executes the transition:
  `EpMapperServer.cpp`, `EpMapperWire.h`, `rpcrt.c`, or `ipc_port.c`.
- Future changes to this header must prove the `PipeServer` registration and
  dispatch topology before making behavior claims.

## Topology

```text
main.cpp
-> new EpMapperServer(pipeServer)
-> EpMapperServer::EpMapperServer
-> pipeServer->Register(MSGID_EPMAPPER, this, Handler)
-> EpMapperServer::Handler
-> MSGID_EPMAPPER_GET_PORT_NAME
-> EpmapperGetPortNameHandler
-> EpMapperWire.h fixed request/reply records
-> endpoint resolution / driver dynamic-port registration
```

The header is the class-declaration node in this topology. It is not the wire
schema owner and not the policy-transition owner.

## Logic Risk

Treating `EpMapperServer.h` as a runtime owner would create false ownership and
encourage source churn in the wrong file. The actual risks around this subsystem
are the endpoint wire shape, RPC string-binding parsing, RPC binding lifetime,
dynamic-port scope, and driver port-filter attachment. Those risks already have
specific owners and gates in SREV-108 and SREV-218.

## Official Shape

No new Windows/API-facing behavior is defined by this header. The official RPC
and string-binding references for the underlying runtime behavior remain in
SREV-108 and SREV-218. This SREV is a local service-topology classification.

## Fix

No source patch. This SREV records the declaration boundary and closes
`EpMapperServer.h` as docs-only coverage. Future behavior patches should target
the executing owner file or wire schema file that owns the relevant transition.

## Acceptance Gate

`docs/plan/check-srev-229.py` validates the draft-07 schema, header declaration
shape, PipeServer registration and dispatch topology in `EpMapperServer.cpp`,
main service startup ownership in `main.cpp`, existing SREV-108/SREV-218 owner
coverage, split ledger fragment, and absence of new source patch requirements.

Runtime/build gate: Windows `SboxSvc` build continues to compile the header and
register `MSGID_EPMAPPER`; dynamic endpoint runtime behavior remains covered by
the open SREV-108 and SREV-218 Windows gates.
