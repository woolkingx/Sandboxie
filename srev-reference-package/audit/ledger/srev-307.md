---
kind: srev-ledger-entry
id: SREV-307
title: Key IE Protected Mode Fake Value Owner
status: source-level classified after official ZwQueryValueKey, KEY_VALUE_PARTIAL_INFORMATION, and IE Protected Mode shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-307-key-ie-protected-mode-fake-value-owner.md
schema: docs/plan/srev-307-key-ie-protected-mode-fake-value-owner.schema.json
checker: docs/plan/check-srev-307.py
runtime_gate: Windows Internet Explorer Protected Mode smoke plus rights-dropped and value-name negative controls before any predicate change
---

### SREV-307: Key IE Protected Mode Fake Value Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official `ZwQueryValueKey`, `KEY_VALUE_PARTIAL_INFORMATION`, and IE Protected Mode shape; comment-only source clarification, no behavior change |
| Evidence | `Key_NtQueryValueKeyFakeForInternetExplorer` is reached only from the `KeyValuePartialInformation` fake-value gate for the Internet Explorer image. After the rights-dropped skip, it fabricates `REG_DWORD` values for the IE Protected Mode group: Zones-path value `2500` returns `3`, `ProtectedModeOffForAllZones` returns `1`, and `NoProtectedModeBanner` returns `1`. Non-matches return `STATUS_BAD_INITIAL_PC`. The old comments called all three branches `hack`. |
| Data | `Key_NtQueryValueKey`, `Key_NtQueryValueKeyFakeForInternetExplorer`, `DLL_IMAGE_INTERNET_EXPLORER`, `SBIE_FLAG_RIGHTS_DROPPED`, `Secure_Init`, `2500`, `\Microsoft\Windows\CurrentVersion\Internet Settings\Zones`, `ProtectedModeOffForAllZones`, `NoProtectedModeBanner`, `REG_DWORD`, `KEY_VALUE_PARTIAL_INFORMATION`, `STATUS_SUCCESS`, and `STATUS_BAD_INITIAL_PC`. |
| Schema | `KEY_IE_PROTECTED_MODE_FAKE_VALUE_OWNER` says `Key_NtQueryValueKeyFakeForInternetExplorer` owns IE Protected Mode `REG_DWORD` fake values for `KeyValuePartialInformation`; `ZwQueryValueKey` owns caller buffer and result-length contract; `KEY_VALUE_PARTIAL_INFORMATION` requires `Type`, `DataLength`, and counted `Data`; `ProtectedModeOffForAllZones` is a local exact-predicate compatibility value because public Microsoft documentation is sparse; this SREV changes comments and proof only. |
| Topology | `NtQueryValueKey caller -> Key_NtQueryValueKey -> Internet Explorer image fake-value gate -> Key_NtQueryValueKeyFakeForInternetExplorer -> not SBIE_FLAG_RIGHTS_DROPPED -> exact Protected Mode value predicate -> synthetic REG_DWORD KEY_VALUE_PARTIAL_INFORMATION`; non-matches continue to normal registry merge/query handling. |
| Logic Risk | Generic `hack` wording hides the legal owner and proof boundary. The stable boundary is IE image, `KeyValuePartialInformation`, not rights-dropped, exact Protected Mode compatibility value, and complete `REG_DWORD` partial-information payload. Since `ProtectedModeOffForAllZones` lacks equally strong public official documentation, future changes must be runtime-proven rather than inferred from the current source comment. |
| Official Shape | Microsoft documents Protected Mode as an IE security mode based on UAC, integrity levels, and UIPI. Microsoft policy docs define the per-zone Protected Mode policy and Zones registry family. Microsoft USD guidance documents `2500` under `Internet Settings\Zones\<n>`, with `0` enabling Protected Mode and `3` disabling it. Microsoft ESC FAQ guidance documents `NoProtectedModeBanner` as a `REG_DWORD` under `Internet Explorer\Main`. Microsoft documents the `ZwQueryValueKey` and `KEY_VALUE_PARTIAL_INFORMATION` buffer shape. |
| Fix | The source comments now name SREV-307, the per-zone Protected Mode value, the Zones path gate, the sparse public-doc caveat for `ProtectedModeOffForAllZones`, the `NoProtectedModeBanner` Microsoft ESC evidence, and the local fake-value owner boundary. No rights-dropped gate, predicate, payload, status, or normal registry path changed. |
| Acceptance Gate | `docs/plan/check-srev-307.py` validates the draft-07 schema, official references, source comment owner, unchanged rights-dropped gate, unchanged `2500`/`ProtectedModeOffForAllZones`/`NoProtectedModeBanner` predicates, unchanged `KEY_VALUE_PARTIAL_INFORMATION` payload construction, stale `hack` wording removal for these branches, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-307.sh` is the targeted wrapper. Runtime gate: Windows Internet Explorer Protected Mode smoke plus rights-dropped and value-name negative controls before any predicate change. |
