# SREV-050: DNS Filter Response Buffer Gates

## Data

`Sandboxie/core/dll/dns_filter.c` `WSA_FillResponseStructure` builds a filtered
DNS `WSAQUERYSETW` response into the caller-provided `lpqsResults` buffer used by
`WSA_WSALookupServiceNextW`.

The packed layout is:

```text
WSAQUERYSETW
ServiceInstanceName
QueryString
CSADDR_INFO[]
SOCKADDR[]
BLOB
HOSTENT
h_name
h_aliases
h_addr_list
IP bytes
```

Before SREV-263, the source still had a comment near the end saying the final
check was a failsafe for wrong size calculations. SREV-263 clarified that this
is only the SREV-050 diagnostic end fence; segment-level `CHECK_BUFFER_SPACE`
gates are the release-mode overflow boundary.

## Official Shape

Microsoft documents `WSALookupServiceNextW` as taking `lpdwBufferLength` as the
number of bytes in the `lpqsResults` buffer on input. If the function fails with
`WSAEFAULT`, `lpdwBufferLength` contains the minimum required size.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsalookupservicenextw
```

Microsoft documents `WSAQUERYSETW` as the result structure containing
`lpcsaBuffer` and `lpBlob` pointers:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw
```

Microsoft documents `BLOB` as a Winsock binary block:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-blob
```

## Schema

Local schema:

```text
docs/plan/srev-050-dns-filter-response-buffer.schema.json
```

The caller buffer has one owner for capacity: `lpdwBufferLength`. The packer may
only write each segment after proving that segment fits between the current
cursor and `bufferEnd`.

## Topology

```text
filtered DNS entries -> WSA_FillResponseStructure -> caller lpqsResults buffer
```

The hook owns the synthetic response layout. Winsock owns the ABI shape and
error contract.

## Logic Risk

Before this patch, `CHECK_BUFFER_SPACE` existed only under `_DEBUG`. Release
builds relied on the precomputed `neededSize` and a final end check after
writing the response. If any size calculation drifted from the write layout, the
release build could write beyond the caller buffer before the final check
noticed.

## Fix

`CHECK_BUFFER_SPACE` now runs in release builds and uses a subtractive
`end - ptr` gate to avoid pointer-addition overflow. `bufferEnd` is available in
all builds. The final check remains as diagnostic defense, but it is no longer
the first release-mode boundary check. SREV-263 later made the final diagnostic
check use the same `bufferEnd` owner instead of recalculating the caller-buffer
end expression.

## Acceptance Gate

`docs/plan/check-srev-050.py` validates the draft-07 schema, official reference
links, release-mode `CHECK_BUFFER_SPACE`, unconditional `bufferEnd`, subtractive
capacity check, diagnostic final-fence ownership, SREV-263 adjacency, and
removal of the `_DEBUG`-only gate.

Windows gate: filtered DNS A/AAAA responses with exact-size, undersized,
oversized, long-domain, and many-address buffers should return either a valid
packed response or `WSAEFAULT` with the required buffer length and no caller
buffer overrun.
