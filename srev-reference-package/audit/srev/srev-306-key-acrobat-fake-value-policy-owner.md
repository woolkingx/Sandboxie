# SREV-306: Key Acrobat Fake Value Policy Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, Microsoft `ZwQueryValueKey` / `KEY_VALUE_PARTIAL_INFORMATION` documentation, Adobe Acrobat preference references |
| Output artifact | Acrobat fake-value policy owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_NtQueryValueKeyFakeForAcrobatReader` |
| Acceptance gate | Targeted checker validates source comment ownership, unchanged fake-value predicates and payload shape, official references, stale workaround wording removal, combined ledger, and ledger fragment |

## Data

`Key_NtQueryValueKey` handles caller `ValueName` as a counted
`UNICODE_STRING` view and, before entering the merge path, has a
`KeyValuePartialInformation` fake-value dispatch surface:

```text
KeyValueInformationClass == KeyValuePartialInformation
  -> KeyValueInformation != NULL
  -> ResultLength != NULL
  -> image-specific fake-value owner
  -> STATUS_BAD_INITIAL_PC means fall through to normal merge/query handling
```

The Acrobat branch is shared by `DLL_IMAGE_ACROBAT_READER`,
`DLL_IMAGE_PLUGIN_CONTAINER`, `DLL_IMAGE_GOOGLE_CHROME`, and
`DLL_IMAGE_INTERNET_EXPLORER` for the embedded AcroPDF/browser-plugin path. It
calls `Key_NtQueryValueKeyFakeForAcrobatReader`, which currently fabricates only
two `REG_DWORD` values:

```text
bProtectedMode -> 0
iCheckReader   -> 0
```

The old comments labeled both the dispatcher branch and the fake owner as
`$Workaround$ - 3rd party fix`, which hid the local API shape: this code is not a
general registry bypass. It is a narrow synthetic
`KEY_VALUE_PARTIAL_INFORMATION` producer for specific Adobe preference value
names.

## Official Shape

Microsoft documents `ZwQueryValueKey` as returning a registry value entry into a
caller-allocated `KeyValueInformation` buffer. `KeyValueInformationClass`
selects the returned information shape, `Length` is the buffer size, and
`ResultLength` reports the returned or required byte count.

Microsoft documents `KEY_VALUE_PARTIAL_INFORMATION` as:

```text
TitleIndex
Type
DataLength
Data[1]
```

`DataLength` is the size in bytes of `Data`, and `Type` is the registry value
type tag for that data.

Adobe documents `bProtectedMode` as a `REG_DWORD` boolean preference that
enables Protected Mode for Acrobat/Reader. Adobe's updater quick key documents
`iCheckReader` as the Reader check-mode preference, with `0` meaning "Do not
download or install."

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwqueryvaluekey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_value_partial_information`
- `https://www.adobe.com/devnet-docs/acrobatetk/tools/PrefRef/Windows/Privileged.html`
- `https://www.adobe.com/devnet-docs/acrobatetk/tools/QuickKeys/WIN_UpdaterQuickKeyAll.pdf`

## Schema

Local schema:

```text
docs/plan/srev-306-key-acrobat-fake-value-policy-owner.schema.json
```

Contract id:

```text
KEY_ACROBAT_FAKE_VALUE_POLICY_OWNER
```

## Topology

```text
NtQueryValueKey caller
  -> Key_NtQueryValueKey
  -> KeyValuePartialInformation fake-value gate
  -> Acrobat/AcroPDF-compatible image set
  -> Key_NtQueryValueKeyFakeForAcrobatReader
  -> exact counted value-name predicate
  -> synthetic REG_DWORD KEY_VALUE_PARTIAL_INFORMATION
```

Non-matching value names return `STATUS_BAD_INITIAL_PC` and continue through the
normal registry merge/query path.

## Logic Risk

The old label made this look like an arbitrary third-party compatibility patch.
The stable local boundary is narrower:

```text
Adobe preference value name
  -> complete REG_DWORD KeyValuePartialInformation payload
  -> otherwise fall through unchanged
```

Because this code intentionally changes application-visible registry values,
any future predicate change must be proven with Windows runtime coverage for the
affected Acrobat/Reader/browser-plugin workflow and negative controls for
unrelated registry values.

## Fix

The source comments now name SREV-306, the Acrobat/AcroPDF-compatible
dispatcher, the `KeyValuePartialInformation` fake-value policy, the complete
partial-information buffer requirement, and the fall-through status owner.

No behavior changed: the image predicates, `bProtectedMode` and `iCheckReader`
counted value-name predicates, `REG_DWORD` type, DWORD payloads, `ResultLength`
calculation, `STATUS_SUCCESS` result for matched values, `STATUS_BAD_INITIAL_PC`
fall-through, and normal registry merge/query path are unchanged.
This is a comment-only source clarification, no behavior change.

## Acceptance Gate

`docs/plan/check-srev-306.py` validates the draft-07 schema, official
references, source comment owner, unchanged image/value-name predicates,
unchanged `KEY_VALUE_PARTIAL_INFORMATION` payload construction, stale workaround
wording removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows Acrobat/Reader and AcroPDF/browser-plugin smoke proving
`bProtectedMode` and `iCheckReader` still receive the intended DWORD values,
with negative controls showing unrelated value names fall through to normal
registry merge/query handling before any predicate change.
