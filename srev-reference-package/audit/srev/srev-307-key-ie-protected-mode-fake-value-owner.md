# SREV-307: Key IE Protected Mode Fake Value Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, Microsoft `ZwQueryValueKey` / `KEY_VALUE_PARTIAL_INFORMATION`, Microsoft Internet Explorer Protected Mode references |
| Output artifact | IE Protected Mode fake-value policy owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_NtQueryValueKeyFakeForInternetExplorer` |
| Acceptance gate | Targeted checker validates source comment ownership, unchanged rights-dropped gate, unchanged IE value predicates and payload shape, official references, sparse-doc caveat for `ProtectedModeOffForAllZones`, combined ledger, and ledger fragment |

## Data

`Key_NtQueryValueKeyFakeForInternetExplorer` is reached only from the
`KeyValuePartialInformation` fake-value gate in `Key_NtQueryValueKey` when
`Dll_ImageType == DLL_IMAGE_INTERNET_EXPLORER`.

The function fabricates DWORD partial-information values for several Internet
Explorer compatibility settings. This SREV covers the Protected Mode group:

```text
Zones path + value 2500           -> REG_DWORD 3
ProtectedModeOffForAllZones       -> REG_DWORD 1
NoProtectedModeBanner             -> REG_DWORD 1
```

The Protected Mode group is intentionally skipped when
`SBIE_FLAG_RIGHTS_DROPPED` is set, because the adjacent comment says the
rights-dropped path uses token-information faking in `Secure_Init` to let IE
turn Protected Mode off through its normal privilege checks.

The old comments called the three branches `hack`, which hid two important
boundaries: the fake owner only produces complete
`KEY_VALUE_PARTIAL_INFORMATION` DWORD payloads, and
`ProtectedModeOffForAllZones` does not currently have the same public Microsoft
documentation quality as the `2500` zone value and `NoProtectedModeBanner`.

## Official Shape

Microsoft documents `ZwQueryValueKey` as returning registry value information
into a caller-allocated buffer selected by `KeyValueInformationClass`, with
`Length` and `ResultLength` defining returned or required byte counts.

Microsoft documents `KEY_VALUE_PARTIAL_INFORMATION` as `TitleIndex`, `Type`,
`DataLength`, and inline `Data`.

Microsoft documents Internet Explorer Protected Mode as reducing Internet
Explorer privileges through UAC, integrity levels, and UIPI, and says users can
disable it with a checkbox while administrators can use Group Policy.

Microsoft InternetExplorer Policy CSP documents the per-zone Protected Mode
policy and the `Software\Policies\Microsoft\Windows\CurrentVersion\Internet
Settings\Zones\<n>` registry key family. Microsoft Unified Service Desk
guidance documents the non-policy `2500` value under
`Software\Microsoft\Windows\CurrentVersion\Internet Settings\Zones\<n>`, where
value `0` enables Protected Mode and value `3` disables it.

Microsoft IE ESC FAQ script guidance documents
`HKCU\Software\Microsoft\Internet Explorer\Main\NoProtectedModeBanner` as a
`REG_DWORD` value used to suppress a Protected Mode disabled warning.

No equivalent public Microsoft documentation was found for
`ProtectedModeOffForAllZones` during this pass. SREV-307 therefore records it as
a local exact-predicate compatibility value, not as a Microsoft-defined public
contract.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwqueryvaluekey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_value_partial_information`
- `https://learn.microsoft.com/en-us/windows/win32/win7appqual/protected-mode`
- `https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-internetexplorer`
- `https://learn.microsoft.com/en-us/dynamics365/unified-service-desk/admin/internet-explorer-settings-bpa?view=dynamics-usd-4.3`
- `https://learn.microsoft.com/en-us/troubleshoot/developer/browsers/security-privacy/enhanced-security-configuration-faq`

## Schema

Local schema:

```text
docs/plan/srev-307-key-ie-protected-mode-fake-value-owner.schema.json
```

Contract id:

```text
KEY_IE_PROTECTED_MODE_FAKE_VALUE_OWNER
```

## Topology

```text
NtQueryValueKey caller
  -> Key_NtQueryValueKey
  -> Internet Explorer image fake-value gate
  -> Key_NtQueryValueKeyFakeForInternetExplorer
  -> not SBIE_FLAG_RIGHTS_DROPPED
  -> exact Protected Mode value predicate
  -> synthetic REG_DWORD KEY_VALUE_PARTIAL_INFORMATION
```

The `2500` branch has an additional topology gate:

```text
TruePath contains \Microsoft\Windows\CurrentVersion\Internet Settings\Zones
  -> ValueName == 2500
  -> REG_DWORD 3
```

Non-matching value names return `STATUS_BAD_INITIAL_PC` and continue through the
normal registry merge/query path.

## Logic Risk

The old `hack` wording made these branches look like broad registry bypasses.
The stable boundary is narrower:

```text
IE image
  -> KeyValuePartialInformation
  -> not rights-dropped
  -> exact Protected Mode compatibility value
  -> complete REG_DWORD partial-information payload
```

The `ProtectedModeOffForAllZones` predicate is intentionally not broadened from
source comments alone because its public official documentation is sparse. Any
future change to path guards, values, or rights-dropped behavior requires a
Windows IE/AcroPDF runtime matrix with negative controls.

## Fix

The source comments now name SREV-307, the per-zone Protected Mode value, the
Zones path gate, the sparse public-doc caveat for `ProtectedModeOffForAllZones`,
the `NoProtectedModeBanner` Microsoft ESC evidence, and the local fake-value
owner boundary.

No behavior changed: the `SBIE_FLAG_RIGHTS_DROPPED` skip, value-name lengths,
case-insensitive comparisons, Zones path scan, `REG_DWORD` type, DWORD payloads,
`ResultLength` calculation, `STATUS_SUCCESS`, `STATUS_BAD_INITIAL_PC`, and
normal registry merge/query path are unchanged.
This is a comment-only source clarification, no behavior change.

## Acceptance Gate

`docs/plan/check-srev-307.py` validates the draft-07 schema, official
references, source comment owner, unchanged rights-dropped gate, unchanged
`2500`/`ProtectedModeOffForAllZones`/`NoProtectedModeBanner` predicates,
unchanged `KEY_VALUE_PARTIAL_INFORMATION` payload construction, stale `hack`
wording removal for these three branches, combined ledger entry, and split
ledger fragment.

Runtime gate: Windows Internet Explorer Protected Mode smoke proving the three
fake DWORD values still produce the intended compatibility behavior, plus
negative controls for rights-dropped processes, non-Zones `2500`, unrelated
value names, and normal registry merge/query handling before any predicate
change.
