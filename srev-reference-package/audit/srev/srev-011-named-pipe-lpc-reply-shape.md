# SREV-011 Named-Pipe LPC Connect Reply Shape

Status: source-level spec before patch.

## Official Boundary Notes

Microsoft documents `winternl.h` as the surface for internal Windows APIs, and
states that these APIs are internal to Windows, can change between releases, and
should be loaded dynamically when used. The public Microsoft Learn `winternl.h`
function index does not expose a dedicated `NtConnectPort` contract page.

Implication: `NtConnectPort` connection-info semantics are an internal Windows
boundary. For this patch, do not infer new OS behavior. Preserve the existing
Sandboxie proxy behavior and harden only the local `SbieDll` / `SbieSvc` reply
wire shape.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/devnotes/calling-internal-apis
- https://learn.microsoft.com/en-us/windows/win32/api/winternl/

## Local Wire Schema

Owner: `Sandboxie/core/svc/namedpipewire.h`

```c
struct tagNAMED_PIPE_LPC_CONNECT_RPL
{
    MSG_HEADER h;
    ULONG handle;
    ULONG max_msg_len;
    ULONG info_len;
    UCHAR info_data[1];
};
```

`MSG_HEADER.length` is the allocated reply byte length transported by
`SbieDll_CallServer`. `PipeServer::AllocMsg(length)` writes that length into the
reply header. `SbieDll_CallServer` allocates exactly that reply length plus a
small guard and copies received LPC chunks until the declared reply length is
collected.

The legal successful old-LPC connect reply must therefore satisfy:

```text
h.length >= FIELD_OFFSET(NAMED_PIPE_LPC_CONNECT_RPL, info_data)
info_len <= h.length - FIELD_OFFSET(NAMED_PIPE_LPC_CONNECT_RPL, info_data)
copy_len = min(info_len, caller_connection_info_capacity)
```

Failed replies may legally be `SHORT_REPLY(status)` and contain only
`MSG_HEADER`, but successful replies cannot be short because the caller reads
`handle`, `max_msg_len`, `info_len`, and optional `info_data`.

## Risk

The pre-patch caller has a no-op clamp:

```c
if (rpl->info_len < info_len)
    info_len = info_len;
```

Then it copies `info_len` bytes from `rpl->info_data`. If a malformed or stale
reply reports success but carries less payload than `info_len`, the DLL can read
past the received reply buffer and copy unowned bytes into the caller buffer.

## Acceptance Gate

- No `info_len = info_len` no-op remains.
- Successful replies must prove `h.length` covers the fixed reply fields before
  `handle`, `max_msg_len`, or `info_data` are trusted.
- `info_len` must fit inside the reply payload.
- `memcpy` must use `min(reply_info_len, caller_capacity)`.
