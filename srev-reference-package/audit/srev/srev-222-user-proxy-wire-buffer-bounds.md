# SREV-222 User Proxy Wire Buffer Bounds

## Data

Owner files:

```text
Sandboxie/core/svc/UserServer.cpp
Sandboxie/core/svc/UserWire.h
Sandboxie/core/dll/file.c
```

Reviewed nodes:

```text
QueueServer::PutReqHandler
SbieDll_QueueGetReq
UserServer::QueueCallbackWorker2
UserServer::OpenFile
UserServer::OpenDocument
USER_OPEN_FILE_REQ
USER_SHELL_EXEC_REQ
File_NtCreateFileProxy
RtlInitUnicodeString
NtCreateFile
ShellExecuteExW
```

## Schema

`USER_PROXY_WIRE_BUFFER_BOUNDS` defines these local contracts:

- Queue request data is caller-controlled wire data until the user-proxy worker
  validates the request length and offsets.
- `QueueCallbackWorker2` may read a `msgid` only after `data_len >=
  sizeof(ULONG)`.
- `USER_OPEN_FILE_REQ.FileNameOffset` and
  `USER_SHELL_EXEC_REQ.FileNameOffset` must point inside the received request
  buffer, after the fixed header, on a `WCHAR` boundary, and to a
  NUL-terminated string fully contained in the request buffer.
- `USER_OPEN_FILE_REQ.EaBufferOffset` is optional, but when it is nonzero, the
  `[EaBufferOffset, EaBufferOffset + EaLength)` range must stay inside the
  received request buffer.
- `File_NtCreateFileProxy` must not copy a trailing `WCHAR` from the caller's
  counted `UNICODE_STRING`; it copies exactly `ObjectName->Length` bytes and
  synthesizes the NUL terminator in the local request buffer.
- This SREV does not change EFS policy, path-list matching, request ids,
  queue ownership, requested file access, share access, create disposition,
  create options, shell verb choice, or broker handle duplication.

## Topology

```text
sandboxed caller
  -> SbieDll_QueuePutReq(*USERPROXY_session, data, data_len)
  -> QueueServer stores caller data by length
  -> user proxy worker receives data_ptr/data_len
  -> msgid gate
  -> USER_OPEN_FILE / USER_SHELL_EXEC fixed header gate
  -> bounded string/range extraction
  -> NtCreateFile or ShellExecuteExW
```

The queue carrier proves only the byte extent of the message. `UserWire.h`
defines the semantic shape layered on top of those bytes, so the user proxy
must validate offsets before treating them as C strings or optional buffers.

## Logic Risk

Before this SREV, `QueueCallbackWorker2` read `*(ULONG *)data_ptr` before
proving that the queued payload contained four bytes. `QueueServer::PutReqHandler`
allows nonzero request data lengths up to `PIPE_MAX_DATA_LEN`, so a 1-3 byte
request can reach the user-proxy worker.

`OpenFile` and `OpenDocument` also trusted caller-provided offsets before using
the pointed data with string APIs. A malformed `FileNameOffset` could point
outside the fixed request body or to a non-terminated buffer, after which
`_wcsnicmp`, `wcslen`, `RtlInitUnicodeString`, or `ShellExecuteExW` could scan
beyond the queue allocation. `OpenFile` also trusted `EaBufferOffset` and
`EaLength` before passing the optional EA buffer to `NtCreateFile`.

The DLL producer had the dual counted-string bug: `NtCreateFile` receives an
`OBJECT_ATTRIBUTES` whose `ObjectName` is a counted `UNICODE_STRING`, but
`File_NtCreateFileProxy` copied `Length + sizeof(WCHAR)` from that source
buffer. A counted Unicode string is not guaranteed to provide a readable
trailing NUL, so the producer must synthesize the terminator in the local wire
buffer.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitstring
- https://learn.microsoft.com/en-us/windows/win32/api/ntdef/nf-ntdef-initializeobjectattributes
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecuteexw
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow

## Fix

`QueueCallbackWorker2` now returns a status reply for payloads shorter than a
message id instead of dereferencing the buffer.

`UserServer.cpp` now owns small wire helpers for bounded string and range
extraction. `OpenFile` and `OpenDocument` use them before any path policy,
`wcslen`, `RtlInitUnicodeString`, `NtCreateFile`, or `ShellExecuteExW` call.
Malformed offsets, unbounded strings, and out-of-buffer EA ranges return
`STATUS_INFO_LENGTH_MISMATCH`.

`File_NtCreateFileProxy` now treats `ObjectAttributes->ObjectName->Length` as
the counted source byte length, rejects odd byte lengths and request-size
overflow, copies exactly those bytes, and writes a local NUL terminator into
the queued request buffer.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-222.py
bash docs/plan/check-srev-222.sh
```

Runtime/build gate still required:

- Windows service/DLL build for `UserServer.cpp` and `file.c`.
- Negative `USERPROXY` queue smoke for data lengths 1, 2, and 3 returning
  `STATUS_INFO_LENGTH_MISMATCH` without worker crash.
- Negative `USER_OPEN_FILE` and `USER_SHELL_EXEC` smokes for out-of-range,
  unaligned, pre-header, and unterminated `FileNameOffset` values.
- Negative `USER_OPEN_FILE` smoke for out-of-range `EaBufferOffset + EaLength`.
- Positive EFS `USER_OPEN_FILE` and `BreakoutDocument` smokes proving normal
  producer requests still broker `NtCreateFile` and `ShellExecuteExW`.
