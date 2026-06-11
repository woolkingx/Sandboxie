# SREV-263: DNS Filter Final Fence Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/dns_filter.c`, SREV-050, Microsoft Winsock references |
| Output artifact | `docs/plan/srev-263-dns-filter-final-fence-owner.schema.json`, `docs/plan/check-srev-263.py`, `docs/plan/check-srev-263.sh`, ledger fragment, source clarification |
| Owner | `WSA_FillResponseStructure` final diagnostic buffer fence |
| Acceptance gate | targeted source checker plus SREV-050 adjacency checker, core coverage, and diff checkpoint |

## Evidence

SREV-050 already owns the release-mode buffer contract for
`WSA_FillResponseStructure`: every packed segment write must pass
`CHECK_BUFFER_SPACE(currentPtr, size, bufferEnd)` before the write, and
`lpdwBufferLength` is the caller-provided byte capacity / required-size owner.

The remaining source comment still said the final check was a lightweight
failsafe for wrong size calculations. That wording obscured the real topology:
the final check is not the write boundary. It is a diagnostic end fence after
the segment gates have already protected the caller buffer.

## Official Shape

Microsoft documents `WSALookupServiceNextW` as receiving `lpdwBufferLength` with
the number of bytes in the caller's `lpqsResults` buffer on input; on
`WSAEFAULT`, it contains the minimum required byte count. Microsoft documents
`WSAQUERYSETW` as the result structure containing pointer fields such as
`lpcsaBuffer` and `lpBlob`. Microsoft documents `BLOB` as Winsock binary block
storage.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsalookupservicenextw
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-blob
```

## Data

`WSA_FillResponseStructure`, caller `lpqsResults`, caller `lpdwBufferLength`,
`bufferEnd`, `CHECK_BUFFER_SPACE`, packed `WSAQUERYSETW`, `CSADDR_INFO`,
`SOCKADDR`, `BLOB`, `HOSTENT`, and SREV-050.

## Schema

`DNS_FILTER_FINAL_FENCE_OWNER` says:

- SREV-050 owns the response buffer capacity contract;
- `CHECK_BUFFER_SPACE` gates each release-mode segment write against
  `bufferEnd`;
- the final end check is diagnostic only and uses the same `bufferEnd` owner;
- this SREV does not change response layout, required-size calculation,
  `WSAEFAULT` behavior, HOSTENT relative-offset encoding, or DNS filter policy.

## Topology

```text
lpdwBufferLength input capacity
  -> bufferEnd
  -> per-segment CHECK_BUFFER_SPACE before writes
  -> final diagnostic currentPtr <= bufferEnd fence
```

## Logic Risk

Calling the final check a failsafe for wrong size calculations can invite the
wrong repair: relying on an after-the-fact fence instead of preserving the
pre-write segment gates. The correct owner is SREV-050's `bufferEnd` contract;
the final check is only a diagnostic consistency fence.

## Fix

The source comment now names SREV-050 as the final diagnostic fence owner and
states that segment-level `CHECK_BUFFER_SPACE` gates are the release-mode
overflow boundary. The final check now compares `currentPtr` to the already
computed `bufferEnd`, keeping the capacity owner single-sourced. No layout or
runtime policy changed.

## Acceptance Gate

`docs/plan/check-srev-263.py` validates the draft-07 schema, official
references, source comment, final `bufferEnd` fence, unchanged release-mode
segment gates, SREV-050 adjacency, and the ledger fragment.

Runtime gate: inherited from SREV-050.
