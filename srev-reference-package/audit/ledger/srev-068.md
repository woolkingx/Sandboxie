---
kind: srev-ledger-entry
id: SREV-068
title: Winsock Proxy Sockaddr Gate
status: patched-source-level-after-official-connect-wsaconnect-connectex-sockaddr-shape-
owner: Sandboxie/core/dll/net.c
spec: docs/plan/srev-068-winsock-proxy-sockaddr-gate.md
schema: docs/plan/srev-068-winsock-proxy-sockaddr-gate.schema.json
checker: docs/plan/check-srev-068.py
runtime_gate: "proxy-enabled IPv4/IPv6 connect routing, localhost bypass, bypass-list matching, malformed `name`/`namelen` fallback to provider-owned errors, and ConnectEx overlapped behavior"
---
### SREV-068: Winsock Proxy Sockaddr Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official connect/WSAConnect/ConnectEx sockaddr shape and local proxy routing analysis; needs Windows proxy-enabled Winsock runtime proof |
| Evidence | `Sandboxie/core/dll/net.c` routes `connect`, `WSAConnect`, and `ConnectEx` through proxy logic when `WSA_ProxyEnabled` is set. Microsoft documents those APIs as receiving a `const sockaddr *name` plus `namelen`; invalid `name`/too-small `namelen` belongs to provider-owned `WSAEFAULT` handling. The local proxy helpers dereferenced `sa_family` before proving that `name` was a full AF_INET or AF_INET6 sockaddr, and the hook used unresolved `is_localhost(name)` calls before proxy routing. |
| Data | Caller `name` pointer, caller `namelen` byte count, `sa_family`, AF_INET/AF_INET6 family payloads, localhost decision, bypass-list decision, proxy rule selection, and fallback real Winsock call. |
| Schema | `WINSOCK_PROXY_SOCKADDR_GATE` says Sandboxie's proxy layer may inspect or rewrite a connect address only after `name != NULL`, `namelen >= sizeof(USHORT)`, and a family-specific AF_INET/AF_INET6 length gate. Malformed or unsupported-family addresses must bypass Sandboxie proxy routing and fall through to the real provider. |
| Topology | Caller sockaddr flows through optional Sandboxie network policy and proxy routing, then to the real Winsock connect-family API. Sandboxie owns only the AF_INET/AF_INET6 proxy interpretation layer, not malformed pointer inputs or unsupported families. |
| Logic Risk | With proxy enabled, a null, too-small, or unsupported-family `name` could be dereferenced in Sandboxie's proxy route before the real Winsock provider could return the documented error. That turns a provider-owned invalid-input result into a local crash or wrong routing decision. |
| Official Shape | `docs/plan/srev-068-winsock-proxy-sockaddr-gate.md` records Microsoft `connect`, `WSAConnect`, `ConnectEx`, and sockaddr references. `docs/plan/srev-068-winsock-proxy-sockaddr-gate.schema.json` records the JSON Schema draft-07 local `WINSOCK_PROXY_SOCKADDR_GATE` contract. |
| Fix | `WSA_IsConnectSockaddr` now gates AF_INET/AF_INET6 address interpretation by pointer and length. `WSA_GetIP`, `WSA_BypassProxy`, and `WSA_GetProxy` fail closed on unproven addresses. The three connect-family proxy gates now require the shared sockaddr gate, and `WSA_IsLocalhostAddress` replaces the unresolved `is_localhost(name)` call. The `WSA_GetIP` unsupported-family fallback comment now names SREV-068 local interpretation instead of generic "something is wrong" wording. |
| Acceptance Gate | `docs/plan/check-srev-068.py` validates the draft-07 schema, official references, shared sockaddr gate, guarded `WSA_GetIP`, guarded bypass/proxy helpers, guarded connect-family proxy route, unsupported-family fallback comment, removal of raw `is_localhost(name)`, and ledger entry; `docs/plan/check-srev-068.sh` is the targeted wrapper. Windows gate: proxy-enabled IPv4/IPv6 connect routing, localhost bypass, bypass-list matching, malformed `name`/`namelen` fallback to provider-owned errors, and ConnectEx overlapped behavior. |
