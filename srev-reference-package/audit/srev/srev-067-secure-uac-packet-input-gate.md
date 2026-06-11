# SREV-067: Secure UAC Packet Input Gate

## Data

`Sandboxie/core/dll/secure.c` recognizes AppInfo UAC RPC calls, stores the
result-handle output slot, and later builds a `SECURE_UAC_PACKET` for
Sandboxie Service. Type 1 elevation uses caller-provided `ApplicationName`,
`CommandLine`, and `CurrentDirectory` string pointers from `SECURE_UAC_ARGS`.

The relevant data nodes are:

```text
SECURE_UAC_ARGS type 1 string pointers
type 1 result handle pointer
Secure_Elevation_Type state
SECURE_UAC_PACKET allocation
wcslen length pass
wmemcpy packet serialization pass
```

## Official Shape

Microsoft documents `wcslen` as operating on a null-terminated wide-character
string:

```text
https://learn.microsoft.com/en-us/previous-versions/windows/embedded/ms860442%28v%3Dmsdn.10%29
```

Microsoft documents `wmemcpy` as copying wide characters from a source buffer to
a destination buffer:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-170
```

Those CRT routines do not make null or unproven input pointers legal. The local
UAC packet builder must prove its type 1 string inputs before calling them.

## Schema

Local schema:

```text
docs/plan/srev-067-secure-uac-packet-input-gate.schema.json
```

Type 1 elevation may be accepted only when:

```text
ProcessHandle != NULL
ApplicationName != NULL
CommandLine != NULL
CurrentDirectory != NULL
```

Packet serialization may begin only after `Dll_Alloc(pkt_len)` succeeds.

## Topology

```text
NDR stack args -> Secure_CheckElevation type classification -> Secure_HandleElevation packet builder -> SbieSvc UAC request
```

`Secure_CheckElevation` owns the type 1 argument-shape gate. The packet builder
owns allocation proof before writing the packet.

## Logic Risk

Before this patch, type 1 elevation checked only `ProcessHandle`. If any of the
three string pointers was null, `Secure_HandleElevation` could crash in `wcslen`
or `wmemcpy` while processing a partially recognized UAC call. The packet
builder also wrote to `pkt` immediately after `Dll_Alloc` without checking
allocation success.

## Fix

Type 1 elevation now requires non-null `ApplicationName`, `CommandLine`, and
`CurrentDirectory` before setting `Secure_Elevation_Type`. Packet construction
now returns early if `Dll_Alloc(pkt_len)` fails.

## Acceptance Gate

`docs/plan/check-srev-067.py` validates the draft-07 schema, official CRT
references, type 1 string-pointer gates before `Secure_Elevation_Type = 1`,
packet allocation gate before packet writes, and ledger entry.

Windows gate: normal type 1 elevation and MSI type 2 elevation still build UAC
packets; malformed type 1 calls with missing string pointers fail closed before
global elevation state is set; low-memory allocation failure returns without
packet writes.
