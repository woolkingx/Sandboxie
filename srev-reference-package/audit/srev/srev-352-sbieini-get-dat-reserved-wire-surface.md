# SREV-352: SbieIni GET_DAT Reserved Wire Surface

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/svc/sbieiniserver.cpp`, `Sandboxie/core/svc/sbieiniserver.h`, `Sandboxie/core/svc/sbieiniwire.h`, `Sandboxie/core/svc/msgids.h`, caller search results, and Microsoft native file I/O documentation |
| Output artifact | Comment-only source patch, draft-07 schema, targeted checker, and ledger fragment |
| Owner | `SbieIniServer` home-directory `*.dat` service wire surface |
| Acceptance gate | Targeted checker validates `GET_DAT` remains reserved/unrouted, `SET_DAT` write/delete behavior is unchanged, stale `ToDo` wording is removed, no caller exists for `MSGID_SBIE_INI_GET_DAT`, and ledger fragment is present |

## Data

`SbieIniServer::Handler2` has an active `MSGID_SBIE_INI_SET_DAT` route and a
reserved `MSGID_SBIE_INI_GET_DAT` id. `SetDatFile` accepts an
`SBIE_INI_SETTING_REQ`, limits the target to Sandboxie home-directory
`*.dat` names without `..`, allows only the session leader, and uses the
request value bytes as the file payload or deletes the file when `value_len`
is zero.

`sbieiniwire.h` defines generic setting request/reply shapes, but it does not
define a dat-file read reply shape with file size, byte count, buffer cap, or
partial-read contract. Local search found no caller that sends
`MSGID_SBIE_INI_GET_DAT`.

Before this SREV, the inactive `GetDatFile` block ended with a bare `ToDo`.
That wording hid the real boundary: readback is not just the inverse of write.
It needs a reply schema and file-size gate before it can safely become a routed
service operation.

## Official Shape

Microsoft documents `NtCreateFile` as producing a file handle for subsequent
file operations, and documents `NtReadFile` as reading bytes into a caller
provided buffer with `IO_STATUS_BLOCK.Information` receiving the number of
bytes read. The current active `SET_DAT` path uses native file I/O for write
and delete. A future read path would need to choose the desired access, file
sharing, synchronous/asynchronous mode, read length, EOF handling, and reply
buffer shape explicitly.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntreadfile`

## Schema

Local schema:

```text
docs/plan/srev-352-sbieini-get-dat-reserved-wire-surface.schema.json
```

Contract id:

```text
SBIEINI_GET_DAT_RESERVED_WIRE_SURFACE
```

## Boundary

```text
client request
  -> MSGID_SBIE_INI_SET_DAT active write/delete route
  -> SbieIniServer::SetDatFile
  -> Sandboxie home-directory *.dat file

client request
  -> MSGID_SBIE_INI_GET_DAT reserved id
  -> no handler route until read reply schema exists
```

`SbieIniServer` owns the broker route. `sbieiniwire.h` owns the request/reply
shape. Windows native file I/O owns file read/write semantics. The reserved id
must not be routed through the active setting request shape as if the read
schema already existed.

## Topology

```text
SET_DAT
  -> caller must be the session leader
  -> setting must be a terminated *.dat name without ..
  -> SbieApi_GetHomePath + setting builds the target path
  -> value_len == 0 deletes
  -> otherwise NtCreateFile(FILE_GENERIC_WRITE, FILE_OVERWRITE_IF)
  -> NtWriteFile(value, value_len)

GET_DAT
  -> reserved msgid
  -> no active handler
  -> future route requires reply schema, max read size, EOF behavior, and caller gate
```

## Logic Risk

The stale `ToDo` can make the missing read route look like a simple feature
hole. It is actually a schema gap. A read broker must decide how large a file
may be, how the reply buffer represents bytes, which caller may read it, and
whether the path policy is identical to `SET_DAT` or stricter.

## Fix

Comment-only source clarification. The source now names SREV-352, marks
`MSGID_SBIE_INI_GET_DAT` as a reserved wire id, and names the missing read
reply schema, length cap, file-size gate, and authorization model. No msgid,
request structure, `SET_DAT` validation, home path construction, `NtDeleteFile`,
`NtCreateFile`, `NtWriteFile`, or caller behavior changed.

## Acceptance Gate

`docs/plan/check-srev-352.py` validates the draft-07 schema, official
references, reserved `GET_DAT` source comments, inactive route/prototype shape,
active `SET_DAT` session-leader and path gates, absence of `GET_DAT` callers,
stale `ToDo` removal, combined ledger entry, and split ledger fragment.

Runtime gate: none for this comment-only classification. A future `GET_DAT`
implementation would need a Windows broker read smoke with valid/invalid
callers, missing file, large file, exact cap, delete/write/read sequencing, and
malformed path names.
