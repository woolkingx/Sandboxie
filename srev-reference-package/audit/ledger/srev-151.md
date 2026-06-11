---
kind: srev-ledger-entry
id: SREV-151
title: Named Pipe Read Reply Actual Length
status: patched-source-level-after-official-ntreadfile-and-local-named-pipe-wire-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/namedpipewire.h
spec: docs/plan/srev-151-namedpipe-read-reply-actual-length.md
schema: docs/plan/srev-151-namedpipe-read-reply-actual-length.schema.json
checker: docs/plan/check-srev-151.py
runtime_gate: Windows named-pipe short-read, cancel, and malformed-reply runtime proof
---

### SREV-151: Named Pipe Read Reply Actual Length

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `NtReadFile` / `IO_STATUS_BLOCK` and local named-pipe wire review; needs Windows named-pipe runtime proof |
| Evidence | `Sandboxie/core/svc/namedpipewire.h` was the top unnamed reviewable core file after SREV-150. It defines `NAMED_PIPE_READ_REQ.read_len` and `NAMED_PIPE_READ_RPL.data_len` for the read proxy shared by `Sandboxie/core/svc/namedpipeserver.cpp` and `Sandboxie/core/dll/file_pipe.c`. Before this SREV, `ReadHandler` set `rpl->data_len = req->read_len` before calling `NtReadFile`, returned `IoStatusBlock.Information`, but did not use it to size the reply payload. `File_NtReadFile` then copied `rpl->data_len` bytes without proving that the reply tail contained that many bytes or that `data_len <= Length`. |
| Data | `NAMED_PIPE_READ_REQ.read_len`, `NAMED_PIPE_READ_RPL.data_len`, `NAMED_PIPE_READ_RPL.iosb.information`, `NtReadFile` `Length`, `IO_STATUS_BLOCK.Information`, caller `Length`, reply `h.length`, `NamedPipeServer::ReadHandler`, and `File_NtReadFile`. |
| Schema | `NAMEDPIPE_READ_REPLY_ACTUAL_LENGTH` says `read_len` is the maximum requested byte count and caller buffer size, `IO_STATUS_BLOCK.Information` is the completed read transfer count, `data_len` is the actual transfer length present in the reply tail, completed read replies satisfy `data_len <= read_len` and `FIELD_OFFSET(NAMED_PIPE_READ_RPL, data) + data_len <= h.length` even for warning-status partial transfers, timeout/cancel replies force `data_len = 0`, and the DLL copy gate proves both caller-buffer and reply-tail bounds before copying. |
| Topology | Legal flow is caller `Length`, DLL sends `NAMED_PIPE_READ_REQ.read_len`, SbieSvc `ReadHandler` calls `NtReadFile(..., req->read_len, ...)`, completed `IO_STATUS_BLOCK.Information` becomes reply `data_len`, DLL validates reply tail length and caller `Length`, then copies exactly `data_len` bytes. |
| Logic Risk | Requested length and completed transfer length are different nodes. Treating requested length as reply `data_len` makes short reads, EOF-style reads, or cancelled reads look like full-buffer transfers on the local wire and lets the DLL copy bytes that were not reported as actually read or that are not present in a malformed reply tail. |
| Official Shape | `docs/plan/srev-151-namedpipe-read-reply-actual-length.md` records Microsoft `NtReadFile`, `IO_STATUS_BLOCK`, and I/O status block references. `docs/plan/srev-151-namedpipe-read-reply-actual-length.schema.json` records the JSON Schema draft-07 local `NAMEDPIPE_READ_REPLY_ACTUAL_LENGTH` contract. |
| Fix | `ReadHandler` now allocates from `FIELD_OFFSET(NAMED_PIPE_READ_RPL, data)`, zeroes `IO_STATUS_BLOCK`, initializes `data_len` to zero, calls `NtReadFile` with `req->read_len`, derives `data_len` from bounded `IO_STATUS_BLOCK.Information`, and forces timeout/cancel or impossible over-report paths to zero payload. `File_NtReadFile` now validates the fixed reply header, `data_len <= Length`, and `data_len <= h.length - FIELD_OFFSET(NAMED_PIPE_READ_RPL, data)` before copying. |
| Acceptance Gate | `docs/plan/check-srev-151.py` validates the draft-07 schema, official references, read request/reply wire shape, service-side actual-transfer-length contract, DLL-side reply-tail and caller-buffer copy gate, stale requested-length assignment removal, and the ledger fragment; `docs/plan/check-srev-151.sh` is the matrix wrapper. Runtime/build gate: Windows DLL/SbieSvc build; named-pipe short-read and partial-read smoke proving only `IO_STATUS_BLOCK.Information` bytes are returned and copied; timeout/cancel smoke proving `data_len = 0`; malformed service-reply fault injection proving DLL rejects `data_len > Length` or `data_len` beyond `h.length`. |
