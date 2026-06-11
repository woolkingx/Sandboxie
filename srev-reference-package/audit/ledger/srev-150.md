---
kind: srev-ledger-entry
id: SREV-150
title: COM Invoke Wire Buffer Bound
status: patched-source-level-after-official-rpcolemessage-and-local-com-wire-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/comwire.h
spec: docs/plan/srev-150-com-invoke-wire-buffer-bound.md
schema: docs/plan/srev-150-com-invoke-wire-buffer-bound.schema.json
checker: docs/plan/check-srev-150.py
runtime_gate: Windows COM proxy build and oversized RPCOLEMESSAGE buffer runtime proof
---

### SREV-150: COM Invoke Wire Buffer Bound

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `RPCOLEMESSAGE` / `IRpcChannelBuffer::SendReceive` and local COM wire review; needs Windows COM proxy runtime proof |
| Evidence | `Sandboxie/core/svc/comwire.h` was the top unnamed reviewable core file after SREV-149. It defines the shared COM proxy wire records used by `Sandboxie/core/dll/com.c` and `Sandboxie/core/svc/comserver.cpp`. `COM_INVOKE_METHOD_REQ` carries `RPCOLEMESSAGE.cbBuffer` bytes for `IRpcChannelBuffer::SendReceive`. Before this SREV, `ComServer::InvokeMethodHandler` rejected invoke buffers at or above the shared-map capacity before copying into `COM_SLAVE_MAP`, but DLL `Com_IRpcChannelBuffer_SendReceive` did not apply the same bound before allocation and copy. It also computed request length with `sizeof(COM_INVOKE_METHOD_REQ) + pMessage->BufferLength` even though the request is a flexible-tail wire record. |
| Data | `RPCOLEMESSAGE.cbBuffer`, `COM_INVOKE_METHOD_REQ.BufferLength`, `COM_INVOKE_METHOD_REQ.Buffer`, `COM_SLAVE_MAP.BufferLength`, `COM_SLAVE_MAP.Buffer`, `COM_MAX_INVOKE_BUF_LEN`, `Com_IRpcChannelBuffer_SendReceive`, and `ComServer::InvokeMethodHandler`. |
| Schema | `COM_INVOKE_WIRE_BUFFER_BOUND` says `RPCOLEMESSAGE.cbBuffer` is a byte count, the invoke payload must fit the SbieSvc shared COM map before DLL allocation/copy, DLL sender and service receiver must use the same named maximum, flexible-tail request length is `FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer) + BufferLength`, and COM policy is unchanged. |
| Topology | Legal flow is COM proxy `RPCOLEMESSAGE.cbBuffer`, DLL sender validates `cbBuffer < COM_MAX_INVOKE_BUF_LEN`, DLL builds `COM_INVOKE_METHOD_REQ` using the flexible-tail offset, SbieSvc receiver revalidates the same bound, then copies schema-valid bytes into `COM_SLAVE_MAP` for slave stub invocation. |
| Logic Risk | Wire validation must happen before the first allocation/copy at each owner boundary. Receiver-only maximum enforcement lets an oversized `RPCOLEMESSAGE.cbBuffer` force the DLL sender to allocate and copy a request that the service will later reject. |
| Official Shape | `docs/plan/srev-150-com-invoke-wire-buffer-bound.md` records Microsoft `RPCOLEMESSAGE`, `IRpcChannelBuffer::SendReceive`, and `IRpcChannelBuffer::GetBuffer` references. `docs/plan/srev-150-com-invoke-wire-buffer-bound.schema.json` records the JSON Schema draft-07 local `COM_INVOKE_WIRE_BUFFER_BOUND` contract. |
| Fix | `comwire.h` now names the shared map size, fixed header length, and maximum invoke payload length. `comserver.cpp` derives its receiver-side `MAX_MAP_BUFFER_LENGTH` from that shared constant. `Com_IRpcChannelBuffer_SendReceive` rejects `pMessage->BufferLength >= COM_MAX_INVOKE_BUF_LEN` before request allocation and computes request length from `FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer)`. |
| Acceptance Gate | `docs/plan/check-srev-150.py` validates the draft-07 schema, official references, shared wire constants, DLL sender bound-before-allocation ordering, flexible-tail request length, service receiver use of the shared bound, and the ledger fragment; `docs/plan/check-srev-150.sh` is the matrix wrapper. Runtime/build gate: Windows DLL/SbieSvc build; normal COM proxy calls still invoke through `IRpcChannelBuffer::SendReceive`; oversized synthetic `RPCOLEMESSAGE.cbBuffer` fails in the DLL sender with `MEM_E_INVALID_SIZE` before request allocation/copy; receiver still rejects malformed or oversized wire requests. |
