---
kind: srev-ledger-entry
id: SREV-306
title: Key Acrobat Fake Value Policy Owner
status: source-level classified after official ZwQueryValueKey, KEY_VALUE_PARTIAL_INFORMATION, and Adobe preference shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-306-key-acrobat-fake-value-policy-owner.md
schema: docs/plan/srev-306-key-acrobat-fake-value-policy-owner.schema.json
checker: docs/plan/check-srev-306.py
runtime_gate: Windows Acrobat/Reader and AcroPDF/browser-plugin smoke plus negative value-name controls before any predicate change
---

### SREV-306: Key Acrobat Fake Value Policy Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official `ZwQueryValueKey`, `KEY_VALUE_PARTIAL_INFORMATION`, and Adobe preference shape; comment-only source clarification, no behavior change |
| Evidence | `Key_NtQueryValueKey` routes only `KeyValuePartialInformation` queries with non-null output/result buffers to image-specific fake-value owners before entering the registry merge path. The Acrobat branch is shared by Acrobat Reader, plugin-container, Chrome, and Internet Explorer for AcroPDF/browser-plugin compatibility. `Key_NtQueryValueKeyFakeForAcrobatReader` only fabricates `REG_DWORD` values for counted value names `bProtectedMode` and `iCheckReader`; non-matches return `STATUS_BAD_INITIAL_PC` and fall through. The old comments labeled the dispatcher and owner only as `$Workaround$ - 3rd party fix`. |
| Data | `Key_NtQueryValueKey`, `KeyValuePartialInformation`, `Key_NtQueryValueKeyFakeForAcrobatReader`, `DLL_IMAGE_ACROBAT_READER`, `DLL_IMAGE_PLUGIN_CONTAINER`, `DLL_IMAGE_GOOGLE_CHROME`, `DLL_IMAGE_INTERNET_EXPLORER`, `bProtectedMode`, `iCheckReader`, `REG_DWORD`, `KEY_VALUE_PARTIAL_INFORMATION`, `ResultLength`, `STATUS_SUCCESS`, and `STATUS_BAD_INITIAL_PC`. |
| Schema | `KEY_ACROBAT_FAKE_VALUE_POLICY_OWNER` says `Key_NtQueryValueKeyFakeForAcrobatReader` owns only Adobe preference `REG_DWORD` fake values for `KeyValuePartialInformation`; `ZwQueryValueKey` owns the caller buffer, `Length`, `ResultLength`, and `KeyValueInformationClass` contract; `KEY_VALUE_PARTIAL_INFORMATION` requires `Type`, `DataLength`, and counted `Data` bytes; non-matches must return `STATUS_BAD_INITIAL_PC`; this SREV changes comments and proof only. |
| Topology | `NtQueryValueKey caller -> Key_NtQueryValueKey -> KeyValuePartialInformation fake-value gate -> Acrobat/AcroPDF-compatible image set -> Key_NtQueryValueKeyFakeForAcrobatReader -> exact counted value-name predicate -> synthetic REG_DWORD KEY_VALUE_PARTIAL_INFORMATION`; non-matches continue to the normal registry merge/query path. |
| Logic Risk | Generic third-party workaround wording hides the stable local boundary. This branch does not own broad registry policy; it owns complete partial-information fabrication for two Adobe preference values. Since it intentionally changes application-visible registry values, future predicate changes require Windows Acrobat/Reader/browser-plugin runtime proof and negative controls. |
| Official Shape | Microsoft documents `ZwQueryValueKey` as returning registry value information into a caller-allocated buffer selected by `KeyValueInformationClass`, with `Length` and `ResultLength` defining returned or required byte counts. Microsoft documents `KEY_VALUE_PARTIAL_INFORMATION` as `TitleIndex`, `Type`, `DataLength`, and inline `Data`. Adobe documents `bProtectedMode` as a `REG_DWORD` preference for Protected Mode and `iCheckReader` as the Reader updater check-mode preference where `0` means no download or install. |
| Fix | The source comments now name SREV-306, the Acrobat/AcroPDF-compatible dispatcher, the `KeyValuePartialInformation` fake-value policy, the complete partial-information buffer requirement, and the fall-through status owner. No image predicate, value-name predicate, `REG_DWORD` type, DWORD payload, `ResultLength` calculation, `STATUS_SUCCESS`, `STATUS_BAD_INITIAL_PC`, or normal registry path changed. |
| Acceptance Gate | `docs/plan/check-srev-306.py` validates the draft-07 schema, official references, source comment owner, unchanged image/value-name predicates, unchanged `KEY_VALUE_PARTIAL_INFORMATION` payload construction, stale workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-306.sh` is the targeted wrapper. Runtime gate: Windows Acrobat/Reader and AcroPDF/browser-plugin smoke plus negative value-name controls before any predicate change. |
