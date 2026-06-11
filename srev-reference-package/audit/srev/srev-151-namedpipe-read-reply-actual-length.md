# SREV-151: Named Pipe Read Reply Actual Length

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/namedpipewire.h`, `Sandboxie/core/svc/namedpipeserver.cpp`, `Sandboxie/core/dll/file_pipe.c`, Microsoft `NtReadFile` and `IO_STATUS_BLOCK` references |
| Output artifact | `docs/plan/srev-151-namedpipe-read-reply-actual-length.schema.json`, `docs/plan/check-srev-151.py`, `docs/plan/check-srev-151.sh`, ledger fragment |
| Owner | Named pipe read broker wire reply between sandboxed DLL and SbieSvc |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows named pipe runtime proof remains required |

## Evidence

`Sandboxie/core/svc/namedpipewire.h` became the top unnamed reviewable core file
after SREV-150. It defines `NAMED_PIPE_READ_REQ.read_len` and
`NAMED_PIPE_READ_RPL.data_len` for the read proxy shared by the sandboxed DLL and
SbieSvc.

Before this SREV, `NamedPipeServer::ReadHandler` allocated a reply for
`req->read_len` bytes, set `rpl->data_len = req->read_len`, and passed that same
requested length to `NtReadFile`. It returned `IoStatusBlock.Information` but did
not use it to size the reply payload. `File_NtReadFile` then copied
`rpl->data_len` bytes to the caller buffer without proving that the reply tail
contained that many bytes or that `data_len <= Length`.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntreadfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_io_status_block
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/i-o-status-blocks

## Data

`NAMED_PIPE_READ_REQ.read_len`, `NAMED_PIPE_READ_RPL.data_len`,
`NAMED_PIPE_READ_RPL.iosb.information`, `NtReadFile` `Length`,
`IO_STATUS_BLOCK.Information`, caller `Length`, reply `h.length`,
`NamedPipeServer::ReadHandler`, and `File_NtReadFile`.

## Schema

`NAMEDPIPE_READ_REPLY_ACTUAL_LENGTH` says:

- `read_len` is the maximum requested byte count and caller buffer size.
- `IO_STATUS_BLOCK.Information` is the completed read transfer count.
- `NAMED_PIPE_READ_RPL.data_len` is the actual number of bytes present in the
  reply tail, not the requested maximum.
- Completed read replies must satisfy `data_len <= read_len` and
  `FIELD_OFFSET(NAMED_PIPE_READ_RPL, data) + data_len <= h.length`, even when
  the completion status is a warning such as a partial message transfer.
- Timeout or cancelled read replies force `data_len = 0`.
- The DLL copy gate must prove `data_len <= Length` and `data_len` fits inside
  the received reply before copying.

## Topology

Legal read flow:

```text
caller Length
  -> DLL sends NAMED_PIPE_READ_REQ.read_len
  -> SbieSvc ReadHandler calls NtReadFile(..., req->read_len, ...)
  -> completed IO_STATUS_BLOCK.Information becomes reply data_len when bounded
  -> DLL validates reply tail length and caller Length
  -> DLL copies exactly data_len bytes
```

## Logic Risk

Requested length and completed transfer length are different nodes. Treating the
requested length as reply `data_len` makes short reads, EOF-style reads, or
cancelled reads look like full-buffer transfers on the local wire. The DLL side
then trusts the service reply length and can copy bytes that were not reported as
actually read, or copy beyond a malformed reply tail.

## Fix

`ReadHandler` now allocates the reply from the flexible-tail offset, zeroes the
I/O status block, initializes `data_len` to zero, calls `NtReadFile` with
`req->read_len`, and sets `data_len` only from bounded
`IO_STATUS_BLOCK.Information`. Timeout/cancel paths force a cancelled status and
zero transfer count. If a completed read reports more bytes than were requested,
the service converts the reply to `STATUS_INVALID_PARAMETER` with no payload.

`File_NtReadFile` now validates that the received reply contains the read reply
fixed header, that `data_len <= Length`, and that the reply tail contains
`data_len` bytes before copying.

## Acceptance Gate

`docs/plan/check-srev-151.py` validates the draft-07 schema, official
references, read request/reply wire shape, service-side actual-transfer-length
contract, DLL-side reply-tail and caller-buffer copy gate, stale requested-length
assignment removal, and the ledger fragment. `docs/plan/check-srev-151.sh` is
the matrix wrapper.

Runtime/build gate: Windows DLL/SbieSvc build; named-pipe short-read and partial
read smoke proving only `IO_STATUS_BLOCK.Information` bytes are returned and
copied; timeout/cancel smoke proving `data_len = 0`; malformed service-reply
fault injection proving DLL rejects `data_len > Length` or `data_len` beyond
`h.length`.
