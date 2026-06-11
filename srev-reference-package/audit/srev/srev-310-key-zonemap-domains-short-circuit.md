# SREV-310: Key ZoneMap Domains Short-Circuit

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/key_merge.c`, `Sandboxie/core/svc/filewire.h`, SREV-033, Microsoft `ZwEnumerateKey` / `KEY_NODE_INFORMATION` documentation |
| Output artifact | ZoneMap Domains merge short-circuit boundary, request allocation gate, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_ShouldNotMerge` |
| Acceptance gate | Targeted checker validates source comment ownership, client-side allocation gate before wire writes, unchanged Domains predicates and service probe wire shape, official references, SREV-033 adjacency, stale hack wording removal, combined ledger, and ledger fragment |

## Data

`Key_Merge` normally builds a merged host+box view for registry subkeys and
values. `Key_ShouldNotMerge` has a special ZoneMap Domains branch:

```text
TruePath under HKLM/HKCU Internet Settings\ZoneMap\Domains
  -> ask SbieSvc whether the corresponding sandbox copy key exists
  -> if SbieSvc proves the box Domains key is absent
  -> return TRUE so Key_Merge can skip merging the very large host subtree
```

The old comment called this a `hack` for large numbers of subkeys, typically
created by SpyBot S&D Immunize, because `SHLWAPI!ZoneCheckUrlEx` can spend a
long time enumerating and merging all keys under:

```text
Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains
```

The branch builds a `FILE_CHECK_KEY_EXISTS_REQ` and sends it to SbieSvc. Before
this SREV, it wrote `req->h.length`, `req->h.msgid`, and `req->KeyPath_len`
immediately after `Dll_AllocTemp(req_len)`, without proving the allocation
succeeded.

## Official Shape

Microsoft documents `ZwEnumerateKey` as returning information about a subkey of
an open registry key. The `Index` parameter selects the numbered subkey, and
`ResultLength` reports returned or required bytes. Microsoft documents
`KEY_NODE_INFORMATION` as the shape used for `KeyNodeInformation`, including
`LastWriteTime`, class metadata, and a counted non-null-terminated `Name`.

The large-Domains branch exists because full merge enumeration ultimately has to
walk this subkey namespace. The official enumeration APIs define the host tree
shape; the Sandboxie short-circuit is a local virtual-view optimization and must
not be mistaken for Windows enumeration truth.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwenumeratekey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_node_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_key_information_class`

## Schema

Local schema:

```text
docs/plan/srev-310-key-zonemap-domains-short-circuit.schema.json
```

Contract id:

```text
KEY_ZONEMAP_DOMAINS_SHORT_CIRCUIT
```

SREV-033 owns the `FILE_CHECK_KEY_EXISTS_REQ` wire string shape:

```text
MSG_HEADER
KeyPath_len bytes, including trailing NUL WCHAR
KeyPath[KeyPath_len / sizeof(WCHAR)]
```

## Topology

```text
Key_Merge
  -> Key_ShouldNotMerge(TruePath, CopyPath)
  -> HKLM/HKCU ZoneMap\Domains predicate
  -> FILE_CHECK_KEY_EXISTS_REQ allocation
  -> SbieSvc CheckKeyExists for box key path
  -> STATUS_OBJECT_NAME_NOT_FOUND / STATUS_OBJECT_PATH_NOT_FOUND
  -> cache absence and short-circuit merge
```

Allocation-failure topology:

```text
Dll_AllocTemp(req_len) fails
  -> Key_ShouldNotMerge returns FALSE
  -> Key_Merge keeps normal merge behavior
```

SbieSvc owns the box-key existence proof because in-process `NtOpenKey` can be
brokered by applications such as Adobe Reader X and produce a false success for
the sandbox copy key.

## Logic Risk

The old `hack` comment described the symptom and the workaround but not the
owner boundary. The legal decision is:

```text
Only SbieSvc STATUS_OBJECT_NAME_NOT_FOUND / STATUS_OBJECT_PATH_NOT_FOUND proves
the sandbox Domains copy key is absent enough to short-circuit merge.
```

Allocation failure, call-server failure, or any other status must preserve
normal merge behavior. Otherwise the optimization can become a correctness bug
by treating an unproven absence as a proven absence.

## Fix

The source comment now names SREV-310, the ZoneMap Domains short-circuit owner,
the SbieSvc box-key existence probe, the Adobe Reader broker reason, and the
fail-open-to-normal-merge rule for probe failure.

`Key_ShouldNotMerge` now checks `Dll_AllocTemp(req_len)` before writing the
`FILE_CHECK_KEY_EXISTS_REQ`. On allocation failure it returns `FALSE`, keeping
normal merge behavior instead of crashing or incorrectly proving absence.

No Domains path predicate, HKLM/HKCU split, wire request layout, service message
id, SbieSvc status interpretation, or successful short-circuit behavior changed.

## Acceptance Gate

`docs/plan/check-srev-310.py` validates the draft-07 schema, official
references, source comment owner, allocation gate before request writes,
unchanged Domains predicates and `FILE_CHECK_KEY_EXISTS_REQ` wire shape,
SREV-033 adjacency, stale `hack` wording removal, combined ledger entry, and
split ledger fragment.

Runtime gate: Windows registry smoke for ZoneMap Domains with no box copy key,
with a box copy key, with SbieSvc not returning an absence status, and with
allocation-failure injection proving normal merge behavior is preserved.
