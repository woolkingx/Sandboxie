# SREV-068: Winsock Proxy Sockaddr Gate

## Data

`Sandboxie/core/dll/net.c` routes `connect`, `WSAConnect`, and `ConnectEx`
through Sandboxie's network filtering, bind-IP, and proxy layers. The proxy path
needs the caller's `name` and `namelen` inputs to read `sa_family`, choose an
IPv4 or IPv6 proxy rule, and optionally bypass localhost or bypass-list entries.

The relevant data nodes are:

```text
connect/WSAConnect/ConnectEx name pointer
connect/WSAConnect/ConnectEx namelen byte count
SOCKADDR sa_family
SOCKADDR_IN / SOCKADDR_IN6_LH family-specific payload
proxy routing decision
local Winsock fallback call
```

## Official Shape

Microsoft documents `connect` as receiving a `const sockaddr *name` and
`namelen` byte count. `WSAEFAULT` covers an invalid user-space address, an
incorrect address format for the address family, or a too-small `namelen`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-connect
```

Microsoft documents `WSAConnect` with the same `name` and `namelen` shape. Its
`WSAEFAULT` case includes invalid `name`/`namelen` or too-small `namelen`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsaconnect
```

Microsoft documents `ConnectEx` with the same `name` and `namelen` shape. Its
`WSAEFAULT` case includes invalid `name` or too-small `namelen`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/mswsock/nc-mswsock-lpfn_connectex
```

Microsoft's Winsock sockaddr definition says the first `u_short` is the address
family and the total memory buffer size is `namelen`; the structure is then
interpreted by address family:

```text
https://learn.microsoft.com/en-us/windows/win32/winsock/sockaddr-2
```

## Schema

Local schema:

```text
docs/plan/srev-068-winsock-proxy-sockaddr-gate.schema.json
```

Sandboxie's proxy layer may inspect or rewrite a caller address only when:

```text
name != NULL
namelen >= sizeof(USHORT)
sa_family == AF_INET  -> namelen >= sizeof(SOCKADDR_IN)
sa_family == AF_INET6 -> namelen >= sizeof(SOCKADDR_IN6_LH)
```

Any other family, null pointer, or too-small length must skip Sandboxie's proxy
routing and continue to the underlying Winsock API so the real provider owns the
official error result.

## Topology

```text
caller sockaddr -> Sandboxie filter/bind/proxy routing -> real Winsock connect API
```

The proxy routing layer owns only AF_INET and AF_INET6 connect addresses. It
does not own malformed pointer inputs or non-IP address-family interpretation.

## Logic Risk

Before this patch, the proxy path called `is_localhost(name)`,
`WSA_BypassProxy(name, namelen)`, and `WSA_GetProxy(name, namelen, ...)` without
first proving that `name` pointed to a full IPv4 or IPv6 sockaddr. Both bypass
and proxy helpers dereferenced `sa_family` directly. With proxy enabled, a null,
too-small, or unsupported-family `name` could crash or be routed through a proxy
decision before the real Winsock provider could apply the documented
`WSAEFAULT`/family-specific behavior.

## Fix

`WSA_IsConnectSockaddr` now proves the AF_INET/AF_INET6 sockaddr shape before
Sandboxie proxy routing reads `sa_family` or passes the address to bypass/proxy
helpers. `WSA_BypassProxy`, `WSA_GetProxy`, and `WSA_GetIP` now fail closed on
unproven address inputs. The three connect-family hooks enter proxy routing only
after the shape gate passes; otherwise they fall through to the existing real
Winsock call path.

`WSA_IsLocalhostAddress` replaces the unresolved local `is_localhost` call with
a local helper that also uses the same sockaddr gate.

The `WSA_GetIP` unsupported-family fallback comment now names this SREV-068
gate instead of using generic "something is wrong" wording. That keeps the
reason local to the schema: unsupported or malformed address families are not
locally interpreted by Sandboxie's proxy layer.

## Acceptance Gate

`docs/plan/check-srev-068.py` validates the draft-07 schema, official Microsoft
references, shared sockaddr gate, guarded `WSA_GetIP`, guarded proxy helpers,
removal of the raw `is_localhost(name)` calls, and ledger entry.

Windows gate: with proxy enabled, valid IPv4 and IPv6 `connect`/`WSAConnect`/
`ConnectEx` still route through configured proxy rules; localhost addresses
still bypass proxy; malformed `name`/`namelen` inputs reach the underlying
Winsock provider and return provider-owned errors instead of crashing in
Sandboxie's proxy routing layer.
