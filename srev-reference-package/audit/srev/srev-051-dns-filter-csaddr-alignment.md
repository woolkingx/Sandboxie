# SREV-051: DNS Filter CSADDR_INFO Alignment

## Data

`Sandboxie/core/dll/dns_filter.c` `WSA_FillResponseStructure` packs a
`WSAQUERYSETW` response into one caller buffer. `WSAQUERYSETW.lpcsaBuffer`
points into that packed buffer at a `CSADDR_INFO[]` array.

## Official Shape

Microsoft documents `WSAQUERYSETW.lpcsaBuffer` as an `LPCSADDR_INFO` member:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw
```

Microsoft documents `CSADDR_INFO` as a structure containing `SOCKET_ADDRESS`
members:

```text
https://learn.microsoft.com/en-us/windows/win32/api/ws2def/ns-ws2def-csaddr_info
```

The local `SOCKET_ADDRESS` definition contains a pointer member, so the packed
`CSADDR_INFO[]` cursor must be pointer-aligned before it is cast and assigned.

## Schema

Local schema:

```text
docs/plan/srev-051-dns-filter-csaddr-alignment.schema.json
```

The cursor and required-size formula share the same alignment rule:

```text
align to sizeof(void*) before CSADDR_INFO[]
```

## Topology

```text
wide DNS strings -> aligned CSADDR_INFO[] -> SOCKADDR[] -> BLOB/HOSTENT
```

The DNS hook owns the packed response layout. Winsock owns the ABI shape of
`WSAQUERYSETW.lpcsaBuffer` and `CSADDR_INFO`.

## Logic Risk

Before this patch, two WCHAR strings were packed immediately before
`CSADDR_INFO[]`. Their combined byte length can leave the cursor only
2-byte-aligned on 64-bit builds, after which the code casts the cursor to
`PCSADDR_INFO` and writes pointer-bearing fields.

## Fix

`WSA_FillResponseStructure` now aligns `neededSize` before adding the
`CSADDR_INFO[]` size and aligns `currentPtr` before assigning
`lpqsResults->lpcsaBuffer`.

## Acceptance Gate

`docs/plan/check-srev-051.py` validates the draft-07 schema, official reference
links, `ALIGN_SIZE`, required-size alignment before `csaddrSize`, runtime cursor
alignment before `lpcsaBuffer`, and ledger entry.

Windows gate: filtered DNS A/AAAA responses with odd/even domain WCHAR lengths
on x86, x64, and ARM64/ARM64EC should return naturally aligned `CSADDR_INFO`
buffers and unchanged DNS data.
