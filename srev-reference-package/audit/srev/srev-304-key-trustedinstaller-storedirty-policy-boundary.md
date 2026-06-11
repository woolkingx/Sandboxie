# SREV-304: Key TrustedInstaller StoreDirty Policy Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, Microsoft `ZwSetValueKey` documentation, SREV-213 |
| Output artifact | TrustedInstaller StoreDirty policy boundary, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_NtSetValueKey` |
| Acceptance gate | Targeted checker validates source comment ownership, unchanged StoreDirty predicate, official references, SREV-213 counted-name adjacency, stale workaround wording removal, and ledger fragment |

## Data

`Key_NtSetValueKey` normalizes `ValueName` into a counted `UNICODE_STRING`
view, routes the real write through `__sys_NtSetValueKey`, and has a
TrustedInstaller-specific branch:

```text
Dll_ImageType == DLL_IMAGE_TRUSTED_INSTALLER
  -> ValueName length == 10 WCHARs
  -> ValueName == StoreDirty
  -> return STATUS_SUCCESS without calling __sys_NtSetValueKey
```

The old source comment described this as a workaround for WinSxS assembly
installation where TrustedInstaller alternately creates and deletes
`StoreDirty` under `\REGISTRY\MACHINE\COMPONENTS`, then may abort when the value
still exists. The comment did not name the registry API owner, counted-name
shape, or runtime gate for any future predicate change.

## Official Shape

Microsoft documents `ZwSetValueKey` as creating or replacing a registry value
entry. Its `ValueName` parameter is a `PUNICODE_STRING` naming the value entry;
if the key has no existing matching value, the routine creates a new value
entry with that name. If a matching value exists, it replaces the original
entry.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwsetvaluekey`
- `https://learn.microsoft.com/en-us/windows/win32/sysinfo/registry-value-types`

## Schema

Local schema:

```text
docs/plan/srev-304-key-trustedinstaller-storedirty-policy-boundary.schema.json
```

Contract id:

```text
KEY_TRUSTEDINSTALLER_STOREDIRTY_POLICY_BOUNDARY
```

## Topology

```text
NtSetValueKey caller
  -> Key_NtSetValueKey
  -> counted ValueName normalization
  -> TrustedInstaller StoreDirty policy branch
  -> STATUS_SUCCESS suppression
```

SREV-304 owns only the comment-level classification of this compatibility
policy. SREV-213 owns counted registry value-name handling for delete-v2 and
proves that registry value names crossing these APIs are counted names, not
necessarily caller-terminated strings.

## Logic Risk

Generic workaround wording makes this branch look like an arbitrary skip of a
registry write. The actual boundary is narrower:

```text
TrustedInstaller image
  -> StoreDirty value name
  -> WinSxS COMPONENTS runtime compatibility
```

Because the current source does not prove the key path, type, or data shape at
this branch, this SREV does not add new predicates. Tightening or expanding the
branch requires Windows runtime evidence for WinSxS installation under
Sandboxie, including normal completion and negative controls for non-COMPONENTS
StoreDirty writes.

## Fix

The source comment now names SREV-304, `ZwSetValueKey` create/replace behavior,
the deliberate TrustedInstaller/WinSxS policy boundary, and the Windows runtime
gate for any future predicate change.

No behavior changed: the TrustedInstaller image check, 10-WCHAR counted
`StoreDirty` match, returned `STATUS_SUCCESS`, normal `__sys_NtSetValueKey`
path, and access-denied reopen path are unchanged.
This is a comment-only source clarification, no behavior change.

## Acceptance Gate

`docs/plan/check-srev-304.py` validates the draft-07 schema, official
references, source comment owner, unchanged StoreDirty predicate, unchanged
normal `__sys_NtSetValueKey` path, SREV-213 adjacency, stale workaround wording
removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows TrustedInstaller/WinSxS assembly install smoke proving the
StoreDirty suppression still completes the install, plus negative controls for
non-TrustedInstaller callers and non-COMPONENTS StoreDirty writes before any
predicate change.
