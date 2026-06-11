---
kind: srev-ledger-entry
id: SREV-305
title: Key Classes Enumeration Name Owner
status: source-level classified after official HKCR merged-view and key-name shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-305-key-classes-enumeration-name-owner.md
schema: docs/plan/srev-305-key-classes-enumeration-name-owner.schema.json
checker: docs/plan/check-srev-305.py
runtime_gate: Windows HKU SID Software Classes enumeration smoke for KeyBasicInformation and KeyNodeInformation
---

### SREV-305: Key Classes Enumeration Name Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official HKCR merged-view and key-name shape; comment-only source clarification, no behavior change |
| Evidence | `Key_NtEnumerateKey` merges true/copy registry subkeys and routes selected `KeyBasicInformation` / `KeyNodeInformation` queries to `Key_NtEnumerateKeyFake` when native query would expose an implementation key name rather than the caller-visible child name. One branch detects `\REGISTRY\USER\<sid>\Software\Classes` and fakes the enumeration result. The old comment said native query could return `current_classes` instead of `classes`, but did not name HKCR merged-view topology or the local presentation owner. |
| Data | `Key_NtEnumerateKey`, `KeyBasicInformation`, `KeyNodeInformation`, `Key_NtEnumerateKeyFake`, `SubkeyPath`, `_Registry_User`, `\Software\Classes`, `current_classes`, `Key_Merge`, `Key_NtOpenKeyImpl`, `Key_NtQueryKeyImpl`, and SREV-176. |
| Schema | `KEY_CLASSES_ENUMERATION_NAME_OWNER` says `Key_NtEnumerateKey` owns caller-visible child-name presentation for merged registry enumeration; HKU SID Software Classes enumeration must not expose `current_classes` for `KeyBasicInformation` or `KeyNodeInformation`; `KEY_BASIC_INFORMATION.Name` is a counted non-null-terminated child-name payload; SREV-176 owns `Key_GetName` normalized registry path building; this SREV changes comments and proof only. |
| Topology | `merged registry subkey -> KeyBasicInformation or KeyNodeInformation -> HKU SID Software Classes -> STATUS_ACCESS_DENIED fake-route signal -> Key_NtEnumerateKeyFake`; ordinary subkeys continue to `Key_NtOpenKeyImpl -> Key_NtQueryKeyImpl`. |
| Logic Risk | Calling the native returned name "wrong" without naming the topology can send future work toward the wrong repair. The stable boundary is caller-visible enumeration presentation: for `KeyBasicInformation` and `KeyNodeInformation`, the caller asked for the child name in the enumerated parent namespace. |
| Official Shape | Microsoft documents HKCR as a merged view of HKLM/HKCU `Software\Classes`, and `RegOpenUserClassesRoot` as returning a merged classes-root view for a token's user. Microsoft documents `KEY_BASIC_INFORMATION.NameLength` as a byte count and `Name` as a non-null-terminated child-name array used by `ZwEnumerateKey` / `ZwQueryKey`. |
| Fix | The source comment now names SREV-305, the HKU `<sid>\Software\Classes` caller-visible classes path, the merged classes-root resolution, and the fake-enumeration owner. No `KeyInformationClass` guard, HKU/SID/Software/Classes predicate, `STATUS_ACCESS_DENIED` fake-route signal, native open/query fallback, or `Key_NtEnumerateKeyFake` call changed. |
| Acceptance Gate | `docs/plan/check-srev-305.py` validates the draft-07 schema, official references, source comment owner, unchanged HKU SID Software\Classes predicate, fake-enumeration route, SREV-176 adjacency, stale wrong-name wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-305.sh` is the targeted wrapper. Runtime gate: Windows registry enumeration smoke for `\REGISTRY\USER\<sid>\Software\Classes` proving `KeyBasicInformation` and `KeyNodeInformation` return caller-visible `classes`, while ordinary merged subkeys and `KeyFullInformation` preserve existing behavior. |
