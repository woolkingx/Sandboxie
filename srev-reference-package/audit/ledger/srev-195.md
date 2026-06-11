---
kind: srev-ledger-entry
id: SREV-195
title: COM Blanket Wire String Contract
status: patched-source-level-after-official-cosetproxyblanket-and-coqueryproxyblanket-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/comserver.cpp
spec: docs/plan/srev-195-com-blanket-wire-string-contract.md
schema: docs/plan/srev-195-com-blanket-wire-string-contract.schema.json
checker: docs/plan/check-srev-195.py
runtime_gate: Windows SbieSvc DLL build plus COM QueryBlanket SetBlanket default explicit unterminated principal and reply-shape smoke proof
---
### SREV-195: COM Blanket Wire String Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `CoSetProxyBlanket` and `CoQueryProxyBlanket` shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/comserver.h` was the top unnamed reviewable core file after SREV-194. It exposes `QueryBlanketHandler`, `SetBlanketHandler`, `QueryBlanketSlave`, and `SetBlanketSlave`. The implementation in `Sandboxie/core/svc/comserver.cpp` forwards `COM_SET_BLANKET_REQ::ServerPrincName[128]` to `CoSetProxyBlanket` as an `OLECHAR *` and returns `COM_QUERY_BLANKET_RPL` data through the shared COM slave map. Before this fix, service and slave did not prove that non-default `ServerPrincName` terminated inside the fixed wire field, and `QueryBlanketSlave` did not stamp the produced reply size into `COM_SLAVE_MAP::BufferLength` before the parent copied reply fields. |
| Data | `COM_SET_BLANKET_REQ`, `COM_SET_BLANKET_RPL`, `COM_QUERY_BLANKET_REQ`, `COM_QUERY_BLANKET_RPL`, `DefaultServerPrincName`, `ServerPrincName[128]`, `COM_SLAVE_MAP::BufferLength`, `CoSetProxyBlanket`, `CoQueryProxyBlanket`, `CoTaskMemFree`, `QueryBlanketHandler`, `SetBlanketHandler`, `QueryBlanketSlave`, and `SetBlanketSlave`. |
| Schema | `COM_BLANKET_WIRE_STRING_CONTRACT` says non-default server principal names must terminate inside the fixed wire field before crossing into the shared COM map and again before `CoSetProxyBlanket`; `COLE_DEFAULT_PRINCIPAL` remains represented by `DefaultServerPrincName`; `QueryBlanketSlave` must publish `sizeof(COM_QUERY_BLANKET_RPL)` through `BufferLength`; and `QueryBlanketHandler` must validate that reply shape before copying fields. |
| Topology | Legal `SetBlanket` flow is `DLL SetBlanket hook -> COM_SET_BLANKET_REQ -> SbieSvc fixed length gate -> non-default terminator gate -> shared map -> slave terminator gate -> CoSetProxyBlanket`. Legal `QueryBlanket` flow is `DLL QueryBlanket hook -> SbieSvc QueryBlanketHandler -> slave QueryBlanketSlave -> CoQueryProxyBlanket -> bounded fixed reply copy -> CoTaskMemFree -> BufferLength fixed reply marker -> parent reply copy gate`. |
| Logic Risk | A malformed COM pipe caller could send a fixed `ServerPrincName[128]` without a terminator and make COM scan beyond the wire field. The QueryBlanket path also lacked an explicit reply-shape marker from slave to parent, making the parent copy rely on handler knowledge instead of a shared-map contract. |
| Official Shape | `docs/plan/srev-195-com-blanket-wire-string-contract.md` records Microsoft `CoSetProxyBlanket` and `CoQueryProxyBlanket` references. `docs/plan/srev-195-com-blanket-wire-string-contract.schema.json` records the JSON Schema draft-07 local `COM_BLANKET_WIRE_STRING_CONTRACT` contract. |
| Fix | `comserver.cpp` now has `ComServer_HasWcharTerminator`. `SetBlanketHandler` rejects non-default `ServerPrincName` values that do not terminate within the fixed field; `SetBlanketSlave` repeats the gate before `CoSetProxyBlanket`; `QueryBlanketSlave` sets `pMap->BufferLength = sizeof(COM_QUERY_BLANKET_RPL)` after writing the reply; and `QueryBlanketHandler` validates that size before copying reply fields. |
| Acceptance Gate | `docs/plan/check-srev-195.py` validates the draft-07 schema, official references, `comserver.h` declaration surface, `comwire.h` wire fields, DLL producer shape, service/slave terminator gates, `CoQueryProxyBlanket` ownership release, reply `BufferLength` publication, parent reply-size validation, and split ledger fragment; `docs/plan/check-srev-195.sh` is the matrix wrapper. Runtime gate: Windows SbieSvc/DLL build plus COM `QueryBlanket`/`SetBlanket` smoke for default principal, explicit terminated principal, unterminated principal rejection, and reply-shape copying. |
