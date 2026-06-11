# SREV-190 Winsock ABI Function Pointer Contract

| Field | Content |
|---|---|
| Stage | schema -> boundary -> action -> verify |
| Input Artifact | `Sandboxie/core/dll/wsa_defs.h` and `Sandboxie/core/dll/net.c` Winsock hook topology. |
| Output Artifact | Draft-07 schema, source checker, split ledger fragment, and source readback proving the local Winsock ABI typedefs and detours use the official call shape. |
| Owner | `Sandboxie/core/dll/wsa_defs.h` owns local Winsock function pointer ABI declarations; `Sandboxie/core/dll/net.c` owns the corresponding detour entry points. |
| Acceptance Gate | `docs/plan/check-srev-190.py`, `docs/plan/check-srev-190.sh`, core coverage, full SREV/KPATH matrix, and `git diff --check`. |

## Data

`wsa_defs.h` declares function pointer types used by `net.c`, `proxy.c`, and
`dns_filter.c` for dynamically resolved Winsock and IP helper APIs. These
function pointers are not merely type hints: `net.c` stores original provider
entry points in `__sys_*` variables, installs detours through `SBIEDLL_HOOK`,
and calls extension functions returned by `WSAIoctl(SIO_GET_EXTENSION_FUNCTION_POINTER)`.

The reviewed shapes include:

- `P_WSAStartup`, `P_WSACleanup`, `P_WSAIoctl`, and other hooked Winsock APIs.
- `P_socket`, `P_WSASocketW`, and other APIs returning `SOCKET`.
- `P_WSASetLastError`, which sets thread-local Winsock error state.
- `P_getsockname`, which writes the local socket address into caller storage.
- `P_ConnectEx` and `P_AcceptEx`, which are extension function pointers.
- `P_GetAdaptersAddresses`, which comes from IP Helper rather than Winsock.

## Official API Shape

Microsoft documents `WSAStartup` as `int WSAAPI WSAStartup(...)`. Microsoft
also documents normal Winsock calls such as `send`, `socket`, and `WSAAccept`
with `WSAAPI`. The local detour functions must therefore use the same calling
convention as the functions they replace, especially for 32-bit builds where
calling convention defines stack ownership.

Microsoft documents `socket` as returning `SOCKET`, `WSASetLastError` as
returning no value, and `getsockname` as writing to `sockaddr *name` with
`namelen` as an in/out length. Microsoft documents `ConnectEx` through the
`LPFN_CONNECTEX` extension pointer as returning `BOOL`.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsastartup`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-send`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-socket`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsaaccept`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-wsasetlasterror`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-getsockname`
- `https://learn.microsoft.com/en-us/windows/win32/api/mswsock/nc-mswsock-lpfn_connectex`
- `https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getadaptersaddresses`

## Boundary

The boundary is:

```text
application import / provider extension pointer
-> Sandboxie detour entry point
-> saved original provider function pointer
-> provider-owned implementation
```

At that boundary, the function pointer type and detour function must preserve:

- call convention;
- return width and return semantics;
- writable vs read-only pointer direction for output buffers;
- provider-owned error reporting.

## Topology

The legal topology is:

```text
official Winsock API shape
-> wsa_defs.h function pointer typedef
-> net.c detour prototype and definition
-> SBIEDLL_HOOK / WSAIoctl extension replacement
-> __sys_* original provider call
```

The old topology used plain C function pointers for Winsock APIs and therefore
made the ABI depend on compiler defaults instead of the official API shape.

## Logic Risk

On 32-bit builds, calling a `WSAAPI` provider through a plain C function pointer
can corrupt stack ownership. Returning `int` from APIs whose official return is
`SOCKET` can truncate socket handles on 64-bit. Returning `SOCKET_ERROR` from a
`BOOL` `ConnectEx` detour reports failure as a nonzero success value.

## Fix

- `wsa_defs.h` now marks Winsock function pointer typedefs with `WSAAPI`.
- `P_GetAdaptersAddresses` now uses `WINAPI`.
- `P_socket` and `P_WSASocketW` return `SOCKET`.
- `P_WSASetLastError` returns `void`.
- `P_getsockname` uses a writable `void *name` output pointer.
- `P_ConnectEx` and `P_AcceptEx` return `BOOL`.
- Hooked `net.c` detour prototypes and definitions use `WSAAPI`.
- `WSA_ConnectEx` now returns `FALSE` on local failure paths and stores the
  provider result as `BOOL`.

No proxy rule, bind-IP rule, DNS rule, socket map, or packet filter logic was
otherwise changed.

## Runtime Gate

Linux source checks prove the ABI declarations and local return-shape edits. A
Windows gate remains required: build both x86 and x64, run socket creation,
connect, ConnectEx, send/recv, sendto/recvfrom, bind-IP, proxy, and DNS-filter
paths, and verify no 32-bit stack imbalance or ConnectEx false-success behavior.
