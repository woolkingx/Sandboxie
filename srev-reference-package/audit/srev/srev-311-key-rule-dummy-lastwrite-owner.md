# SREV-311: Key Rule Dummy LastWrite Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/key_merge.c`, Microsoft `ZwQueryKey` / `KEY_NODE_INFORMATION` documentation |
| Output artifact | Rule-specificity dummy subkey LastWriteTime owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_MergeCacheDummys` |
| Acceptance gate | Targeted checker validates source LastWriteTime query before close, zero fallback only after query failure, official references, unchanged rule-specificity topology, stale TODO removal, combined ledger, and ledger fragment |

## Data

`Key_MergeCacheDummys` builds dummy subkeys from readable registry path rules
when rule specificity is enabled and the parent true key is not directly
enumerable. For each readable path under the current `TruePath`, it extracts the
next path component, probes `FakePath` with `SbieApi_OpenKey`, and if that open
succeeds, inserts a `KEY_MERGE_SUBKEY` into `merge->subkeys`.

Before this SREV, the dummy subkey metadata always used:

```text
subkey->LastWriteTime.QuadPart = 0; // todo: fix-me
```

That dummy metadata can flow to `Key_NtEnumerateKeyFake`, which writes the
provided `LastWriteTime` into caller-visible `KEY_BASIC_INFORMATION`,
`KEY_NODE_INFORMATION`, or `KEY_FULL_INFORMATION` output when the actual subkey
open/query path cannot return the native information directly.

## Official Shape

Microsoft documents `KEY_NODE_INFORMATION.LastWriteTime` as the last time the
registry key or one of its values changed, in absolute system time format.
`KEY_NODE_INFORMATION.Name` is a counted non-null-terminated key name.

Microsoft documents `ZwQueryKey` as returning key information for an open key
handle. `KEY_INFORMATION_CLASS` says `KeyBasicInformation` and
`KeyNodeInformation` are legal information classes supplied by `ZwQueryKey` and
`ZwEnumerateKey`.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_node_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwquerykey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_key_information_class`

## Schema

Local schema:

```text
docs/plan/srev-311-key-rule-dummy-lastwrite-owner.schema.json
```

Contract id:

```text
KEY_RULE_DUMMY_LASTWRITE_OWNER
```

## Topology

```text
readable key path rule
  -> Key_MergeCacheDummys
  -> FakePath component
  -> SbieApi_OpenKey proves the key exists/openable
  -> ZwQueryKey(KeyBasicInformation) on that handle
  -> KEY_MERGE_SUBKEY.LastWriteTime
  -> Key_NtEnumerateKeyFake caller-visible metadata if fake route is needed
```

Failure topology:

```text
SbieApi_OpenKey succeeds but ZwQueryKey fails
  -> preserve dummy subkey insertion
  -> LastWriteTime remains zero sentinel
```

## Logic Risk

The old TODO correctly identified that zero was not ideal metadata, but it did
not name the owner boundary. The dummy subkey is rule-derived, but once
`SbieApi_OpenKey(FakePath)` succeeds, the local code already has a handle that
can supply native `KeyBasicInformation.LastWriteTime`. Leaving zero as the
default makes fake enumeration less faithful than necessary.

The safe fallback is still zero because a query failure should not remove a
rule-visible dummy subkey that was already proven openable.

## Fix

`Key_MergeCacheDummys` now calls `__sys_NtQueryKey(KeyBasicInformation)` on the
successfully opened `FakePath` handle before closing it. If the query succeeds
or returns `STATUS_BUFFER_OVERFLOW`, it copies `info.LastWriteTime` into the
dummy `KEY_MERGE_SUBKEY`. If the query fails, it preserves the old zero
fallback.

No readable-path scan, path-component extraction, duplicate suppression, sorted
insert order, `TitleOrClass` policy, or dummy-subkey inclusion behavior changed.

## Acceptance Gate

`docs/plan/check-srev-311.py` validates the draft-07 schema, official
references, source `ZwQueryKey` owner, query-before-close ordering, zero fallback
only after query failure, stale TODO removal, unchanged rule-specificity path
scan and duplicate suppression, combined ledger entry, and split ledger
fragment.

Runtime gate: Windows rule-specificity registry enumeration smoke where a
rule-derived dummy subkey is fake-enumerated and exposes the native
`LastWriteTime`, plus query-failure injection proving the zero fallback still
preserves subkey visibility.
