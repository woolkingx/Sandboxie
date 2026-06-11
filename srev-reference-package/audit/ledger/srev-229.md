---
kind: srev-ledger-entry
id: SREV-229
title: EpMapper Server Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-service-build-proof
owner: Sandboxie/core/svc/EpMapperServer.h
additional_owners:
  - Sandboxie/core/svc/EpMapperServer.cpp
  - Sandboxie/core/svc/EpMapperWire.h
  - Sandboxie/core/dll/rpcrt.c
  - Sandboxie/core/drv/ipc_port.c
spec: docs/plan/srev-229-epmapper-server-header-topology.md
schema: docs/plan/srev-229-epmapper-server-header-topology.schema.json
checker: docs/plan/check-srev-229.py
runtime_gate: Windows SboxSvc build continues to compile the header and register MSGID_EPMAPPER; dynamic endpoint runtime behavior remains covered by the open SREV-108 and SREV-218 Windows gates.
---

### SREV-229: EpMapper Server Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows service build proof |
| Evidence | `Sandboxie/core/svc/EpMapperServer.h` was the top unnamed reviewable core file after SREV-228. Source readback shows it is a declaration-only service header: it includes `PipeServer.h`, declares `class EpMapperServer`, exposes a constructor taking `PipeServer *`, and declares the static PipeServer handler plus `EpmapperGetPortNameHandler`. Runtime and wire ownership live in `EpMapperServer.cpp`, `EpMapperWire.h`, `rpcrt.c`, and `ipc_port.c`. |
| Data | `EpMapperServer`, `PipeServer`, `MSG_HEADER`, `Handler`, `EpmapperGetPortNameHandler`, `MSGID_EPMAPPER`, `MSGID_EPMAPPER_GET_PORT_NAME`, `EPMAPPER_GET_PORT_NAME_REQ`, `EPMAPPER_GET_PORT_NAME_RPL`, `EpMapperServer.cpp`, `EpMapperWire.h`, `rpcrt.c`, and `ipc_port.c`. |
| Schema | `EPMAPPER_SERVER_HEADER_TOPOLOGY_CONTRACT` says `EpMapperServer.h` is a declaration-only service header; it may declare the service class, constructor, static PipeServer handler, and concrete request handler entry point; it does not own RPC endpoint parsing, fixed wire string validation, dynamic-port policy, service control manager lookup, RPC runtime binding lifetime, or driver dynamic-port storage; runtime behavior changes belong to the owner that executes the transition; and future header changes must prove the PipeServer registration and dispatch topology before behavior claims. |
| Topology | `main.cpp -> new EpMapperServer(pipeServer) -> EpMapperServer::EpMapperServer -> pipeServer->Register(MSGID_EPMAPPER, this, Handler) -> EpMapperServer::Handler -> MSGID_EPMAPPER_GET_PORT_NAME -> EpmapperGetPortNameHandler -> EpMapperWire.h fixed request/reply records -> endpoint resolution / driver dynamic-port registration`. |
| Logic Risk | Treating `EpMapperServer.h` as a runtime owner would create false ownership and encourage source churn in the wrong file. SREV-108 already owns the dynamic-port scope and RPC binding lifetime risk in `EpMapperServer.cpp`. SREV-218 already owns the fixed wire string and `ncalrpc:[endpoint]` parsing contract across `EpMapperWire.h`, `EpMapperServer.cpp`, `rpcrt.c`, and `ipc_port.c`. |
| Official Shape | No new Windows/API-facing behavior is defined by this header. The official RPC and string-binding references for the underlying runtime behavior remain in SREV-108 and SREV-218. This SREV is a local service-topology classification. |
| Fix | No source patch. This SREV records the declaration boundary and closes `EpMapperServer.h` as docs-only coverage. Future behavior patches should target the executing owner file or wire schema file that owns the relevant transition. |
| Acceptance Gate | `docs/plan/check-srev-229.py` validates the draft-07 schema, header declaration shape, PipeServer registration and dispatch topology in `EpMapperServer.cpp`, main service startup ownership in `main.cpp`, existing SREV-108/SREV-218 owner coverage, split ledger fragment, and absence of new source patch requirements; `docs/plan/check-srev-229.sh` is the targeted wrapper. Runtime/build gate: Windows `SboxSvc` build continues to compile the header and register `MSGID_EPMAPPER`; dynamic endpoint runtime behavior remains covered by the open SREV-108 and SREV-218 Windows gates. |
