# SREV-150: COM Invoke Wire Buffer Bound

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/comwire.h`, `Sandboxie/core/dll/com.c`, `Sandboxie/core/svc/comserver.cpp`, Microsoft `RPCOLEMESSAGE` and `IRpcChannelBuffer::SendReceive` references |
| Output artifact | `docs/plan/srev-150-com-invoke-wire-buffer-bound.schema.json`, `docs/plan/check-srev-150.py`, `docs/plan/check-srev-150.sh`, ledger fragment |
| Owner | COM invoke method wire request between sandboxed DLL and SbieSvc COM proxy |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows COM proxy runtime proof remains required |

## Evidence

`Sandboxie/core/svc/comwire.h` became the top unnamed reviewable core file after
SREV-149. It defines the COM proxy wire records shared by the sandboxed DLL and
SbieSvc. The highest-risk flexible payload is `COM_INVOKE_METHOD_REQ`, which
wraps `RPCOLEMESSAGE.cbBuffer` bytes for `IRpcChannelBuffer::SendReceive`.

Before this SREV, the SbieSvc receiver rejected invoke buffers at or above its
shared-map capacity before copying into `COM_SLAVE_MAP`. The DLL sender did not
apply the same wire bound before allocation and copy. It also computed request
length as:

```c
sizeof(COM_INVOKE_METHOD_REQ) + pMessage->BufferLength
```

even though `COM_INVOKE_METHOD_REQ` is a flexible-tail wire record. That made
the receiver the first real size gate even though the sender owns allocation and
the first copy from the COM proxy buffer.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/objidlbase/ns-objidlbase-rpcolemessage
- https://learn.microsoft.com/en-us/windows/win32/api/objidlbase/nf-objidlbase-irpcchannelbuffer-sendreceive
- https://learn.microsoft.com/en-us/windows/win32/api/objidlbase/nf-objidlbase-irpcchannelbuffer-getbuffer

## Data

`RPCOLEMESSAGE.cbBuffer`, `COM_INVOKE_METHOD_REQ.BufferLength`,
`COM_INVOKE_METHOD_REQ.Buffer`, `COM_SLAVE_MAP.BufferLength`,
`COM_SLAVE_MAP.Buffer`, `COM_MAX_INVOKE_BUF_LEN`, `Com_IRpcChannelBuffer_SendReceive`,
and `ComServer::InvokeMethodHandler`.

## Schema

`COM_INVOKE_WIRE_BUFFER_BOUND` says:

- `RPCOLEMESSAGE.cbBuffer` is a byte count for the marshaled method buffer.
- The local COM invoke wire payload must fit in the SbieSvc shared COM map
  before the DLL allocates and copies it.
- DLL sender and service receiver must use the same named maximum for invoke
  method payload bytes.
- Flexible-tail request length must be computed from
  `FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer) + BufferLength`, not from
  `sizeof(struct) + BufferLength`.
- The service receiver remains the authority that copies a schema-valid invoke
  request into the slave map; this SREV does not change COM policy.

## Topology

Legal invoke flow:

```text
COM proxy RPCOLEMESSAGE.cbBuffer
  -> DLL SendReceive validates cbBuffer < COM_MAX_INVOKE_BUF_LEN
  -> DLL builds COM_INVOKE_METHOD_REQ using flexible-tail offset
  -> SbieSvc InvokeMethodHandler revalidates BufferLength < COM_MAX_INVOKE_BUF_LEN
  -> service copies bytes into COM_SLAVE_MAP
  -> slave stub invokes the COM method
```

## Logic Risk

Wire validation must happen before the first allocation/copy at each owner
boundary. If only the receiver owns the maximum, an oversized or wrap-prone
`RPCOLEMESSAGE.cbBuffer` can force the DLL sender to allocate and copy a request
that the service will later reject. That is the wrong topology: the sender owns
the request buffer, so it must apply the shared wire bound first.

## Fix

`comwire.h` now names the shared map size, fixed header length, and maximum
invoke payload length. `comserver.cpp` derives its receiver-side
`MAX_MAP_BUFFER_LENGTH` from that shared constant. `Com_IRpcChannelBuffer_SendReceive`
now rejects `pMessage->BufferLength >= COM_MAX_INVOKE_BUF_LEN` before allocating
the request and computes request length from the flexible-tail offset.

## Acceptance Gate

`docs/plan/check-srev-150.py` validates the draft-07 schema, official
references, shared wire constants, DLL sender bound-before-allocation ordering,
flexible-tail request length, service receiver use of the shared bound, and the
ledger fragment. `docs/plan/check-srev-150.sh` is the matrix wrapper.

Runtime/build gate: Windows DLL/SbieSvc build; normal COM proxy calls still
invoke through `IRpcChannelBuffer::SendReceive`; oversized synthetic
`RPCOLEMESSAGE.cbBuffer` fails in the DLL sender with `MEM_E_INVALID_SIZE`
before request allocation/copy; receiver still rejects malformed or oversized
wire requests.
