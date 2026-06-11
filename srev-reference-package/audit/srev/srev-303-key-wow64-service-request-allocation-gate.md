# SREV-303: Key WOW64 Service Request Allocation Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, `Sandboxie/core/svc/filewire.h`, Microsoft WOW64 registry-view references |
| Output artifact | WOW64 registry-view service request contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_FixNameWow64` and `Key_FixNameWow64_2` |
| Acceptance gate | Targeted checker validates source comment owner, service request allocation gate, wire shape, official references, stale TODO removal, and ledger fragment |

## Data

`Key_FixNameWow64` normalizes registry paths after open/create routing. For a
64-bit process that explicitly requests `KEY_WOW64_32KEY`, the local code cannot
rely on a WOW64 thunk around `NtOpenKey`, so it calls `Key_FixNameWow64_2`.

`Key_FixNameWow64_2` builds a `FILE_OPEN_WOW64_KEY_REQ` with:

```text
MSGID_FILE_OPEN_WOW64_KEY
Wow64DesiredAccess = KEY_WOW64_32KEY
KeyPath_len = byte count including terminator
KeyPath = current true registry path
```

Before this SREV, the source carried a stale `ToDo: ???` / disabled
`NoSysCallHooks` comment at the route decision, and `Key_FixNameWow64_2` wrote
the request header immediately after `Dll_AllocTemp(req_len)` without proving
the allocation succeeded.

## Official Shape

Microsoft documents the registry redirector as providing separate logical
registry views for 32-bit and 64-bit applications on WOW64. It maps redirected
keys to physical locations such as `Wow6432Node`, which is reserved and should
not be used as a direct application path.

Microsoft documents `KEY_WOW64_64KEY` and `KEY_WOW64_32KEY` as explicit view
selection flags. `KEY_WOW64_32KEY` accesses a 32-bit key from either a 32-bit or
64-bit application. Microsoft also says alternate-view flags have no effect on
shared registry keys and that child operations should keep using the same flag
after opening an alternate view.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/winprog64/accessing-an-alternate-registry-view`
- `https://learn.microsoft.com/en-us/windows/win32/winprog64/registry-redirector`
- `https://learn.microsoft.com/en-us/windows/win32/sysinfo/32-bit-and-64-bit-application-data-in-the-registry`

## Schema

Local schema:

```text
docs/plan/srev-303-key-wow64-service-request-allocation-gate.schema.json
```

Contract id:

```text
KEY_WOW64_SERVICE_REQUEST_ALLOCATION_GATE
```

## Topology

```text
Key_FixNameWow64
  -> 64-bit process with KEY_WOW64_32KEY
  -> Key_FixNameWow64_2
  -> FILE_OPEN_WOW64_KEY_REQ allocation
  -> SbieSvc FileServer::OpenWow64Key
  -> RegOpenKeyEx(... KEY_WOW64_32KEY ...)
  -> returned key path normalized through Key_GetName
```

`filewire.h` owns the wire data shape. `fileserver.cpp` owns server-side request
validation and the `RegOpenKeyEx` alternate-view operation. `key.c` owns the
client-side request allocation and call-server boundary.

## Logic Risk

The stale `NoSysCallHooks` comment hid the real owner: this path is not about
whether syscall hooks are enabled. It exists because a 64-bit caller has no
WOW64 thunk layer to rewrite a native `NtOpenKey` into the 32-bit registry view.

The unchecked request allocation was a deterministic local crash path under
memory pressure: if `Dll_AllocTemp(req_len)` returned `NULL`, the next writes to
`req->h.length`, `req->h.msgid`, and `req->KeyPath` would dereference `NULL`
before SbieSvc could return a normal failure status.

## Fix

The route comment now names SREV-303 and the service-assisted
`KEY_WOW64_32KEY` owner. The stale `ToDo: ???` and disabled `NoSysCallHooks`
block were removed.

`Key_FixNameWow64_2` now returns `STATUS_INSUFFICIENT_RESOURCES` if
`Dll_AllocTemp(req_len)` fails, before writing the wire request.

No WOW64 flag semantics, `FILE_OPEN_WOW64_KEY_REQ` layout, service message id,
call-server route, `Key_GetName` normalization, or duplicate `Wow6432Node`
cleanup changed.

## Acceptance Gate

`docs/plan/check-srev-303.py` validates the draft-07 schema, official
references, source route comment, client-side allocation gate before request
writes, wire request shape, server-side `RegOpenKeyEx(... KEY_WOW64_32KEY ...)`
adjacency, stale TODO removal, combined ledger entry, and split ledger
fragment.

Runtime gate: Windows x64 registry smoke for 64-bit callers requesting
`KEY_WOW64_32KEY`, shared-key no-op behavior, request-allocation failure
injection returning `STATUS_INSUFFICIENT_RESOURCES`, and existing 32-bit WOW64
caller redirection behavior.
