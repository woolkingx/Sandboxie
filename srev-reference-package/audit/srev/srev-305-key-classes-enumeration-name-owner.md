# SREV-305: Key Classes Enumeration Name Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, Microsoft HKCR merged-view and `KEY_BASIC_INFORMATION` documentation, SREV-176 |
| Output artifact | HKU Software\Classes enumeration presentation contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_NtEnumerateKey` fake-enumeration branch |
| Acceptance gate | Targeted checker validates source comment owner, unchanged HKU SID Software\Classes predicate, fake-enumeration route, official references, SREV-176 adjacency, stale wrong-name wording removal, and ledger fragment |

## Data

`Key_NtEnumerateKey` builds a merged view of true/copy registry subkeys. When a
merged subkey can be represented from cached information, or when native query
would expose a registry implementation name rather than the caller-visible child
name, it routes to `Key_NtEnumerateKeyFake`.

One branch detects:

```text
\REGISTRY\USER\<sid>\Software\Classes
  -> KeyBasicInformation or KeyNodeInformation
  -> fake enumeration result
```

Before this SREV, the source comment said a native query could return
`current_classes` instead of `classes`, and called the returned name "wrong".
The behavior is correct, but the comment did not name the official HKCR
merged-view shape or the local presentation owner.

## Official Shape

Microsoft documents `HKEY_CLASSES_ROOT` as a merged view of
`HKEY_LOCAL_MACHINE\Software\Classes` and
`HKEY_CURRENT_USER\Software\Classes`. `RegOpenUserClassesRoot` returns the
merged classes-root view for the user identified by a token.

Microsoft documents `KEY_BASIC_INFORMATION.NameLength` as the byte length of
the key name string and says the `Name` array is not null-terminated. The same
name member is the caller-visible child-name payload returned by
`ZwEnumerateKey` / `ZwQueryKey` for `KeyBasicInformation`.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/sysinfo/merged-view-of-hkey-classes-root`
- `https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regopenuserclassesroot`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_basic_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwquerykey`

## Schema

Local schema:

```text
docs/plan/srev-305-key-classes-enumeration-name-owner.schema.json
```

Contract id:

```text
KEY_CLASSES_ENUMERATION_NAME_OWNER
```

## Topology

```text
merged registry subkey
  -> KeyBasicInformation / KeyNodeInformation
  -> caller-visible child name required
  -> HKU\<sid>\Software\Classes merged-root case
  -> Key_NtEnumerateKeyFake
```

SREV-305 owns this comment-level classification and proof. SREV-176 owns
`Key_GetName` as the normalized registry path builder and rejects private
`KEY_NAME_INFORMATION` path reconstruction in helper code.

## Logic Risk

Calling the native returned name "wrong" without naming the topology can send a
future change in the wrong direction: either remove the fake route as cosmetic,
or normalize private `current_classes` names after the fact. The stable boundary
is caller-visible enumeration presentation. For `KeyBasicInformation` and
`KeyNodeInformation`, the caller asked for a child name in the enumerated parent
namespace, so the fake owner must return `classes` for the
`\REGISTRY\USER\<sid>\Software\Classes` edge.

## Fix

The source comment now names SREV-305, the HKU `<sid>\Software\Classes`
caller-visible classes path, the merged classes-root resolution, and the
fake-enumeration owner.

No behavior changed: the `KeyInformationClass` guard, HKU/SID/Software/Classes
predicate, `STATUS_ACCESS_DENIED` fake-route signal, native open/query fallback,
and `Key_NtEnumerateKeyFake` call are unchanged.

This is a comment-only source clarification, no behavior change.

## Acceptance Gate

`docs/plan/check-srev-305.py` validates the draft-07 schema, official
references, source comment owner, unchanged HKU SID Software\Classes predicate,
fake-enumeration route, SREV-176 adjacency, stale wrong-name wording removal,
combined ledger entry, and split ledger fragment.

Runtime gate: Windows registry enumeration smoke for
`\REGISTRY\USER\<sid>\Software\Classes` proving `KeyBasicInformation` and
`KeyNodeInformation` return caller-visible `classes`, while ordinary merged
subkeys and `KeyFullInformation` preserve existing behavior.
