---
kind: srev-ledger-entry
id: SREV-218
title: EpMapper Fixed Wire String Contract
status: patched-source-level-after-official-rpc-string-binding-and-msvc-fixed-string-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/EpMapperWire.h
callers:
  - Sandboxie/core/dll/rpcrt.c
  - Sandboxie/core/svc/EpMapperServer.cpp
  - Sandboxie/core/drv/ipc_port.c
spec: docs/plan/srev-218-epmapper-fixed-wire-string-contract.md
schema: docs/plan/srev-218-epmapper-fixed-wire-string-contract.schema.json
checker: docs/plan/check-srev-218.py
runtime_gate: Windows service and DLL build, dynamic spooler resolution, configured RpcPortBindingIfId resolution, configured RpcPortBindingSvc resolution, long and empty RpcPortBinding tag negative tests, malformed service message negative test, and repeated endpoint cache lookup proving valid dynamic ports still resolve and malformed fixed-wire strings fail cleanly.
---

### SREV-218: EpMapper Fixed Wire String Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official RPC string-binding and MSVC fixed-string review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/EpMapperWire.h` defines `EPMAPPER_GET_PORT_NAME_REQ.wszPortId[DYNAMIC_PORT_ID_CHARS]` and `EPMAPPER_GET_PORT_NAME_RPL.wszPortName[DYNAMIC_PORT_NAME_CHARS]`. Before this fix, `Sandboxie/core/dll/rpcrt.c` filled the fixed request field with `wcscpy(req.wszPortId, wszPortId)`, while `Sandboxie/core/svc/EpMapperServer.cpp` consumed `req->wszPortId` directly through string APIs and driver-call parameters after only checking `req->h.length`. The interface-id path also parsed `RpcBindingToStringBindingW` output with `(wchar_t*)pwszPortName + 9` and `wstrPortName[23] = 0`, assuming one observed `ncalrpc:[LRPC-*]` example instead of validating the string-binding field shape. |
| Data | `EPMAPPER_GET_PORT_NAME_REQ`, `EPMAPPER_GET_PORT_NAME_RPL`, `DYNAMIC_PORT_ID_CHARS`, `DYNAMIC_PORT_NAME_CHARS`, `GetDynamicLpcPortName`, `StoreLpcPortName`, `EpmapperGetPortNameHandler`, `RpcBindingToStringBindingW`, `ncalrpc:[endpoint]`, `RpcPortBindingIfId`, `RpcPortBindingSvc`, `RpcPortFilter`, `Open[Name]Endpoint`, and `API_OPEN_DYNAMIC_PORT`. |
| Schema | `EPMAPPER_FIXED_WIRE_STRING_CONTRACT` says `EpMapperWire.h` owns the fixed service wire fields for `MSGID_EPMAPPER_GET_PORT_NAME`; `wszPortId` is a fixed `WCHAR[DYNAMIC_PORT_ID_CHARS]` wire string and must be non-empty and null-terminated inside the field before any string API consumes it; `wszPortName` is a fixed `WCHAR[DYNAMIC_PORT_NAME_CHARS]` wire string and must be null-terminated inside the field before it crosses back to the DLL; the DLL must bounded-copy port ids and cached port names before fixed storage or service-wire send; the service must copy `req->wszPortId` into a bounded local `portId` before policy lookup or driver calls; `RpcBindingToStringBindingW` output must be parsed as a validated `ncalrpc:[endpoint]` string binding before endpoint copy; and the driver `API_OPEN_DYNAMIC_PORT` path keeps its fixed user-string copy gate before `IPC_DYNAMIC_PORT` storage. |
| Topology | DLL config or built-in port id -> `RpcRt_CopyFixedWString` -> `EPMAPPER_GET_PORT_NAME_REQ.wszPortId` -> PipeServer -> `EpMapper_CopyFixedWString` -> local `portId` -> service policy lookup and endpoint resolution -> `RpcBindingToStringBindingW` -> `EpMapper_CopyNcalrpcEndpoint` -> `EPMAPPER_GET_PORT_NAME_RPL.wszPortName` -> `StoreLpcPortName` bounded cache copy. Driver boundary remains `SbieSvc API_OPEN_DYNAMIC_PORT -> Ipc_CopyFixedUserWString -> IPC_DYNAMIC_PORT.wstrPortId/wstrPortName`. |
| Logic Risk | The old code mixed fixed-size wire fields with unbounded null-terminated string assumptions. A malformed or oversized local service message could make `SbieSvc` scan beyond the fixed request field, and a long DLL-side tag could overflow the fixed request before it reached the service. The RPC endpoint parser also depended on a magic offset and a hard-coded example length instead of the official string-binding shape. |
| Official Shape | `docs/plan/srev-218-epmapper-fixed-wire-string-contract.md` records Microsoft `wcscpy_s`, RPC string binding, and `ncalrpc` references. `docs/plan/srev-218-epmapper-fixed-wire-string-contract.schema.json` records the JSON Schema draft-07 local `EPMAPPER_FIXED_WIRE_STRING_CONTRACT` contract. |
| Fix | `rpcrt.c` now uses `RpcRt_CopyFixedWString` before sending `EPMAPPER_GET_PORT_NAME_REQ` and before caching `IPC_DYNAMIC_PORT` entries. `EpMapperServer.cpp` now uses `EpMapper_CopyFixedWString` to validate and copy `req->wszPortId` into local `portId` before all service policy/config/driver uses. `EpMapperServer.cpp` replaces the `+ 9` / `wstrPortName[23]` endpoint parser with `EpMapper_CopyNcalrpcEndpoint`, which validates the `ncalrpc:[` prefix, finds the closing bracket, and rejects endpoints that do not fit. No endpoint policy, dynamic-port filter id policy, SCM lookup behavior, driver API shape, or process-id `0` compatibility path changed. |
| Acceptance Gate | `docs/plan/check-srev-218.py` validates the draft-07 schema, official references, fixed wire arrays, bounded request/cached-string copies, service local `portId` gate before policy use, validated `ncalrpc:[endpoint]` parsing, removal of stale magic endpoint parsing, split ledger fragment, and continued driver-side fixed-string copy gate; `docs/plan/check-srev-218.sh` is the targeted wrapper. Runtime/build gate: Windows service and DLL build, dynamic spooler resolution, configured `RpcPortBindingIfId` resolution, configured `RpcPortBindingSvc` resolution, long/empty `RpcPortBinding` tag negative tests, malformed service message negative test, and repeated endpoint cache lookup proving valid dynamic ports still resolve and malformed fixed-wire strings fail cleanly. |
