# SREV-163: SOCKS5 Byte String Gates

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/proxy.c, Sandboxie/core/dll/net.c, RFC 1928, RFC 1929, and Microsoft C runtime conversion shape
output artifact: bounded SOCKS5 username/password/domain byte-string gates
owner: Sandboxie/core/dll/proxy.c
acceptance gate: docs/plan/check-srev-163.py and docs/plan/check-srev-163.sh
```

## Data

`proxy.c` owns Sandboxie's SOCKS5 client handshake and CONNECT request
construction. `net.c` owns parsing `NetworkUseProxy` settings into
`NETPROXY_RULE` credentials before connect hooks or relay mode pass those
credentials into `proxy.c`.

Before this SREV, the SOCKS5 username/password path converted `WCHAR`
credentials with `wcstombs` without checking `(size_t)-1` conversion failure,
used `SOCKS_AUTH_MAX_SIZE` as both protocol byte maximum and local
null-terminated text storage size, and copied `NetworkUseProxy Login` without
writing an explicit terminator. The optional hostname-resolving CONNECT path
also wrote `strlen(domain)` into the one-byte domain-length field and copied the
domain without first proving it was in the legal SOCKS5 domain-name range.

## Official Shape

- RFC 1928 defines a SOCKS5 CONNECT request and its `ATYP = X'03'`
  domain-name shape as a one-octet name length followed by that many name
  octets:
  `https://www.rfc-editor.org/rfc/rfc1928`.
- RFC 1929 defines username/password subnegotiation with one-octet `ULEN` and
  `PLEN` fields, each followed by 1 to 255 octets:
  `https://www.rfc-editor.org/rfc/rfc1929`.
- Microsoft documents `wcstombs` as converting a wide-character string to a
  multibyte string, returning `(size_t)-1` on conversion failure, and supporting
  a `NULL` destination query for the required byte count:
  `https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/wcstombs-wcstombs-l?view=msvc-170`.

## Schema

`SOCKS5_BYTE_STRING_GATES` says:

- `proxy.c` owns SOCKS5 protocol frame construction.
- `net.c` owns `NetworkUseProxy` config parsing before credentials enter the
  SOCKS5 frame builder.
- `SOCKS_AUTH_MAX_SIZE` is a protocol byte maximum, not a null-terminated
  `WCHAR` storage size.
- local credential text buffers need `SOCKS_AUTH_MAX_SIZE + 1` `WCHAR` slots so
  a 255-character setting still has a terminator.
- `wcstombs` conversion failure is not a legal SOCKS5 field length.
- SOCKS username and password byte fields must be between 1 and 255 bytes after
  conversion before writing `ULEN` or `PLEN`.
- SOCKS domain names must be between 1 and 255 bytes before writing the one-byte
  domain length.
- this SREV does not change proxy selection, bypass policy, socket blocking
  state tracking, relay topology, proxy address parsing, or non-auth SOCKS5
  handshakes.
- Linux source gates are not Windows networking runtime proof.

## Topology

Credential flow:

```text
NetworkUseProxy config -> WSA_ParseNetProxy
NETPROXY_RULE.login/pass as null-terminated WCHAR text
connect / WSAConnect / ConnectEx or relay mode
socks5_auth_field_to_bytes -> 1..255 multibyte octets
socks5_handshake -> RFC 1929 username/password subnegotiation
```

Hostname-resolving flow:

```text
GetAddrInfoW hook -> DNS_LookupMap host bytes
socks5_request -> socks5_request_add_domain
SOCKS5 CONNECT request with ATYP DOMAINNAME and one-octet length
```

## Logic Risk

A failed `wcstombs` returns `(size_t)-1`, which is not a valid protocol length.
Using it in `auth_buf_len` can underflow/overflow the local allocation and then
copy from uninitialized conversion buffers. Separately, treating a one-byte
SOCKS length field as if it could carry an arbitrary `strlen(domain)` can
truncate the length byte and overrun the fixed 264-byte request buffer. The
upstream missing `Login` terminator can also make the conversion scan past the
configured field.

## Fix

`proxy.c` now separates protocol byte maximum from local text storage with
`SOCKS_AUTH_TEXT_SIZE`. `socks5_auth_field_to_bytes` queries the converted
multibyte byte count with `wcstombs(NULL, ...)`, rejects conversion failure,
empty fields, and fields over 255 bytes, then converts exactly the accepted
byte count. `socks5_request_add_domain` rejects empty or over-255-byte domain
names before writing the RFC 1928 one-octet domain length. Relay-mode credential
copies use the text storage size and fail setup if `wcscpy_s` rejects the input.

`net.c` now gives `NETPROXY_RULE.login` and `NETPROXY_RULE.pass` 256 `WCHAR`
slots and explicitly terminates `Login` after copying the counted config value.
The existing password terminators now fit when the configured byte count is 255.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-163.py
bash docs/plan/check-srev-163.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-163.py &&
bash docs/plan/check-srev-163.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows DLL build; SOCKS5 auth smoke with valid ASCII
credentials, invalid/unconvertible credential smoke, 255-byte credential smoke,
over-255-byte credential rejection, hostname-resolving CONNECT smoke with a
legal domain, over-255-byte domain rejection, and normal no-auth SOCKS5 connect
regression smoke.
