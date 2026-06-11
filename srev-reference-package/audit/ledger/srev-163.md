---
kind: srev-ledger-entry
id: SREV-163
title: SOCKS5 Byte String Gates
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/dll/proxy.c
spec: docs/plan/srev-163-socks5-byte-string-gates.md
schema: docs/plan/srev-163-socks5-byte-string-gates.schema.json
checker: docs/plan/check-srev-163.py
runtime_gate: "Windows DLL build, SOCKS5 auth valid invalid boundary smoke, hostname-resolving CONNECT boundary smoke, and no-auth connect regression smoke"
---

### SREV-163: SOCKS5 Byte String Gates

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after SOCKS5 RFC 1928/1929 and Microsoft `wcstombs` shape review; needs Windows networking runtime proof |
| Evidence | `Sandboxie/core/dll/proxy.c` was the top unnamed reviewable core file after SREV-162. It builds SOCKS5 authentication and CONNECT request frames. Before this SREV, `socks5_handshake` used unchecked `wcstombs` return values as username/password byte lengths, local credential arrays used the 255-byte protocol maximum as a null-terminated `WCHAR` storage size, `WSA_ParseNetProxy` copied `Login` without an explicit terminator, and the optional hostname-resolving CONNECT path wrote `strlen(domain)` into a one-byte SOCKS domain-length field without a 1..255-byte gate. |
| Data | `Sandboxie/core/dll/proxy.c`, `Sandboxie/core/dll/net.c`, `socks5_handshake`, `socks5_auth_field_to_bytes`, `socks5_request`, `socks5_request_add_domain`, `NetworkUseProxy`, `NETPROXY_RULE.login`, `NETPROXY_RULE.pass`, `wcstombs`, RFC 1928 domain-name length, and RFC 1929 username/password `ULEN` / `PLEN`. |
| Schema | `SOCKS5_BYTE_STRING_GATES` says `proxy.c` owns SOCKS5 protocol frame construction; `net.c` owns `NetworkUseProxy` config parsing before credentials enter the frame builder; `SOCKS_AUTH_MAX_SIZE` is a protocol byte maximum, not a null-terminated `WCHAR` storage size; local credential text buffers need `SOCKS_AUTH_MAX_SIZE + 1` `WCHAR` slots; `wcstombs` conversion failure is not a legal SOCKS5 field length; SOCKS username and password byte fields must be between 1 and 255 bytes after conversion before writing `ULEN` or `PLEN`; SOCKS domain names must be between 1 and 255 bytes before writing the one-byte domain length; and this SREV does not change proxy selection, bypass policy, socket blocking state tracking, relay topology, proxy address parsing, or non-auth SOCKS5 handshakes. |
| Topology | Legal credential flow is `NetworkUseProxy` config -> `WSA_ParseNetProxy` -> null-terminated `NETPROXY_RULE.login/pass` -> connect hook or relay mode -> `socks5_auth_field_to_bytes` -> RFC 1929 username/password subnegotiation. Legal hostname-resolving flow is `GetAddrInfoW` hook -> `DNS_LookupMap` host bytes -> `socks5_request_add_domain` -> RFC 1928 CONNECT request with one-octet domain length. |
| Logic Risk | `(size_t)-1` from `wcstombs` can poison `auth_buf_len` and copy lengths. A 255-character login without local terminator can make conversion scan past the configured value. A domain name longer than 255 bytes can truncate the length byte and overrun the fixed SOCKS request buffer. |
| Official Shape | `docs/plan/srev-163-socks5-byte-string-gates.md` records RFC 1928, RFC 1929, and Microsoft `wcstombs` references. `docs/plan/srev-163-socks5-byte-string-gates.schema.json` records the JSON Schema draft-07 local `SOCKS5_BYTE_STRING_GATES` contract. |
| Fix | `proxy.c` now defines `SOCKS_AUTH_TEXT_SIZE`, validates `wcstombs` required byte counts through `socks5_auth_field_to_bytes`, rejects empty/over-255-byte/unconvertible credentials, gates domain names through `socks5_request_add_domain`, and checks relay-mode `wcscpy_s` results. `net.c` now stores SOCKS credentials in 256-`WCHAR` arrays and explicitly terminates `Login` with `proxy->login[login_len] = L'\0';` after copying the counted config value. |
| Acceptance Gate | `docs/plan/check-srev-163.py` validates the draft-07 schema, official references, byte/text-size separation, checked credential conversion, domain 1..255-byte gate, relay credential copy gate, `NETPROXY_RULE` storage size, `Login` terminator, ledger entry, and no direct `strlen(domain)` one-byte write. `docs/plan/check-srev-163.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build; SOCKS5 auth smoke with valid ASCII credentials, invalid/unconvertible credential smoke, 255-byte credential smoke, over-255-byte credential rejection, hostname-resolving CONNECT smoke with a legal domain, over-255-byte domain rejection, and normal no-auth SOCKS5 connect regression smoke. |
