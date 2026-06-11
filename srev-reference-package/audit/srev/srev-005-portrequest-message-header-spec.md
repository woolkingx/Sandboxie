# SREV-005 PortRequest Message Header Shape

Status: source-level spec before patch.

## Official Shape

Microsoft's public LPC/ALPC documentation is a carrier/debugging surface, not a
Sandboxie broker payload contract. The `!lpc` debugger documentation describes
LPC ports, queued messages, message IDs, message length/type, and client/server
thread relationships. It also states that LPC is now emulated in ALPC on modern
Windows. The ALPC ETW documentation exposes send, receive, wait-for-reply,
wait-for-new-message, and stop-wait event types.

Those official surfaces prove the boundary is a port-message carrier. They do
not define Sandboxie's service request schema.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc
- https://learn.microsoft.com/en-us/windows/win32/etw/alpc

## Local Shape

Sandboxie's broker request payload starts with:

```c
typedef struct _MSG_HEADER {
    ULONG length;
    union {
        ULONG msgid;
        ULONG status;
    };
} MSG_HEADER;
```

`SbieDll_CallServer` sends the request in LPC chunks. On the first chunk, it
temporarily stores a sequence byte in offset 3 of `MSG_HEADER.length`; the
service clears that byte before assembling the full request.

Therefore the first received payload chunk must contain at least
`sizeof(MSG_HEADER)` bytes before the service may read `length`, `msgid`, or the
sequence byte.

## Local Risk

`PipeServer::PortRequest` previously read `msg_Data[1]`, touched byte offset 3,
and read `msg_Data[0]` before checking `msg->u1.s1.DataLength >=
sizeof(MSG_HEADER)`. A malformed first chunk shorter than the local header could
drive an out-of-bounds read before the broker rejects it.

## Patch Boundary

Reject malformed first chunks before decoding the Sandboxie message header. Keep
the existing chunk assembly protocol, sequence byte, request length checks, and
service dispatch unchanged.

## Acceptance Gate

- A first chunk shorter than `sizeof(MSG_HEADER)` reaches `finish` before
  `msg_Data[0]`, `msg_Data[1]`, or byte offset 3 are read.
- Valid first chunks still use the existing `msgid`, `length`, sequence, and
  `MAX_REQUEST_LENGTH` checks.
- Runtime gate remains open: malformed short LPC payloads of length 0-7 should
  not reach `CallTarget`, and normal multi-chunk broker calls should still work.
