# SREV-231: PStore Server Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-230, `Sandboxie/core/svc/pstoreserver.h` was the top unnamed
reviewable core file. Source readback shows it is the declaration header for the
service-side Protected Storage broker. It includes `PipeServer.h`, declares
`class PStoreServer`, declares the PipeServer handler routes, declares the
worker entry `connectToPStore`, and carries the `m_pStore` provider pointer
slot.

The runtime owners are elsewhere:

- `Sandboxie/core/svc/pstoreserver.cpp` registers `MSGID_PSTORE`, impersonates
  callers, connects to host `pstorec.dll`, and executes PStore broker requests.
- `Sandboxie/core/svc/pstorewire.h` owns the fixed request/reply wire records.
- `Sandboxie/core/dll/ipstore_impl.cpp` and `ipstore_enum.cpp` own the DLL-side
  local `IPStore` implementation and service request producers.
- `Sandboxie/core/dll/pstore.h` owns the generated Protected Storage COM ABI.

SREV-161 already owns the service-side PStore enumeration end-of-sequence
contract. SREV-206 owns the DLL hook output contract for
`PStoreCreateInstance`. SREV-226 owns the local PStore enumerator
`QueryInterface` COM identity contract.

## Data

`PStoreServer`, `PipeServer`, `MSG_HEADER`, `GetTypeInfo`, `GetSubtypeInfo`,
`ReadItem`, `EnumTypes`, `EnumItems`, `connectToPStore`, `m_pStore`,
`MSGID_PSTORE`, `pstoreserver.cpp`, `pstorewire.h`, `ipstore_impl.cpp`,
`ipstore_enum.cpp`, and `pstore.h`.

## Schema

`PSTORE_SERVER_HEADER_TOPOLOGY_CONTRACT` says:

- `pstoreserver.h` is the service-side PStore broker declaration header.
- The header may declare handler entry points and the provider pointer slot.
- The header does not own PStore COM ABI shape, service wire layouts,
  enumeration loop semantics, Protected Storage hook policy, or host
  `pstorec.dll` lifetime behavior.
- Runtime behavior changes belong to `pstoreserver.cpp`, `pstorewire.h`,
  `ipstore_impl.cpp`, `ipstore_enum.cpp`, or `pstore.h`, depending on the
  transition.
- Future header changes must prove PipeServer route topology and provider-state
  ownership before making behavior claims.

## Topology

```text
main.cpp
-> new PStoreServer(pipeServer)
-> PStoreServer::PStoreServer
-> pipeServer->Register(MSGID_PSTORE, this, Handler)
-> QueueUserWorkItem(connectToPStore, this, WT_EXECUTELONGFUNCTION)
-> m_pStore provider slot

sandboxed IPStoreImpl / enumerator producer
-> PSTORE_* wire request
-> PipeServer MSGID_PSTORE
-> PStoreServer::Handler
-> concrete request handler in pstoreserver.cpp
-> host IPStore / pstorec.dll or wire reply
```

The header names the class and state slot; the legal wire and COM contracts live
in the concrete owners listed above.

## Logic Risk

The high coverage score comes from the PStore broker being a boundary-heavy
subsystem: PipeServer, host Protected Storage COM, service impersonation, wire
records, and DLL-side local PStore merge behavior. Patching the header would be
the wrong route unless the bug is in class ownership or provider-state topology.

## Official Shape

No new Windows/API runtime behavior is defined by this header. The official
Protected Storage and COM references remain in SREV-161, SREV-206, and
SREV-226. This SREV is a local service-topology classification.

## Fix

No source patch. This SREV records `pstoreserver.h` as a declaration and
provider-state topology header. Future behavior patches should target the owner
that executes or defines the relevant wire, COM, or provider transition.

## Acceptance Gate

`docs/plan/check-srev-231.py` validates the draft-07 schema, header declaration
shape, service startup and PipeServer registration topology, request dispatch
topology in `pstoreserver.cpp`, existing SREV-161/SREV-206/SREV-226 PStore owner
coverage, split ledger fragment, and absence of runtime owner claims for this
header.

Runtime/build gate: Windows `SboxSvc` build continues to compile the header and
register `MSGID_PSTORE`; PStore runtime behavior remains covered by the open
PStore SREV Windows gates.
