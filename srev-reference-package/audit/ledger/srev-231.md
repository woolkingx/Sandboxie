---
kind: srev-ledger-entry
id: SREV-231
title: PStore Server Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-service-build-proof
owner: Sandboxie/core/svc/pstoreserver.h
additional_owners:
  - Sandboxie/core/svc/pstoreserver.cpp
  - Sandboxie/core/svc/pstorewire.h
  - Sandboxie/core/dll/ipstore_impl.cpp
  - Sandboxie/core/dll/ipstore_enum.cpp
  - Sandboxie/core/dll/pstore.h
spec: docs/plan/srev-231-pstore-server-header-topology.md
schema: docs/plan/srev-231-pstore-server-header-topology.schema.json
checker: docs/plan/check-srev-231.py
runtime_gate: Windows SboxSvc build continues to compile the header and register MSGID_PSTORE; PStore runtime behavior remains covered by the open PStore SREV Windows gates.
---

### SREV-231: PStore Server Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows service build proof |
| Evidence | `Sandboxie/core/svc/pstoreserver.h` was the top unnamed reviewable core file after SREV-230. Source readback shows it is the declaration header for the service-side Protected Storage broker. It includes `PipeServer.h`, declares `class PStoreServer`, declares the PipeServer handler routes, declares the worker entry `connectToPStore`, and carries the `m_pStore` provider pointer slot. Runtime and wire ownership live in `pstoreserver.cpp`, `pstorewire.h`, `ipstore_impl.cpp`, `ipstore_enum.cpp`, and `pstore.h`. |
| Data | `PStoreServer`, `PipeServer`, `MSG_HEADER`, `GetTypeInfo`, `GetSubtypeInfo`, `ReadItem`, `EnumTypes`, `EnumItems`, `connectToPStore`, `m_pStore`, `MSGID_PSTORE`, `pstoreserver.cpp`, `pstorewire.h`, `ipstore_impl.cpp`, `ipstore_enum.cpp`, and `pstore.h`. |
| Schema | `PSTORE_SERVER_HEADER_TOPOLOGY_CONTRACT` says `pstoreserver.h` is the service-side PStore broker declaration header; it may declare handler entry points and the provider pointer slot; it does not own PStore COM ABI shape, service wire layouts, enumeration loop semantics, Protected Storage hook policy, or host `pstorec.dll` lifetime behavior; runtime behavior changes belong to the owner that executes or defines the transition; and future header changes must prove PipeServer route topology and provider-state ownership before behavior claims. |
| Topology | `main.cpp -> new PStoreServer(pipeServer) -> PStoreServer::PStoreServer -> pipeServer->Register(MSGID_PSTORE, this, Handler) -> QueueUserWorkItem(connectToPStore, this, WT_EXECUTELONGFUNCTION) -> m_pStore provider slot`. Request flow is `sandboxed IPStoreImpl / enumerator producer -> PSTORE_* wire request -> PipeServer MSGID_PSTORE -> PStoreServer::Handler -> concrete request handler in pstoreserver.cpp -> host IPStore / pstorec.dll or wire reply`. |
| Logic Risk | The high coverage score comes from the PStore broker being a boundary-heavy subsystem: PipeServer, host Protected Storage COM, service impersonation, wire records, and DLL-side local PStore merge behavior. Patching the header would be the wrong route unless the bug is in class ownership or provider-state topology. |
| Official Shape | No new Windows/API runtime behavior is defined by this header. The official Protected Storage and COM references remain in SREV-161, SREV-206, and SREV-226. This SREV is a local service-topology classification. |
| Fix | No source patch. This SREV records `pstoreserver.h` as a declaration and provider-state topology header. Future behavior patches should target the owner that executes or defines the relevant wire, COM, or provider transition. |
| Acceptance Gate | `docs/plan/check-srev-231.py` validates the draft-07 schema, header declaration shape, service startup and PipeServer registration topology, request dispatch topology in `pstoreserver.cpp`, existing SREV-161/SREV-206/SREV-226 PStore owner coverage, split ledger fragment, and absence of runtime owner claims for this header; `docs/plan/check-srev-231.sh` is the targeted wrapper. Runtime/build gate: Windows `SboxSvc` build continues to compile the header and register `MSGID_PSTORE`; PStore runtime behavior remains covered by the open PStore SREV Windows gates. |
