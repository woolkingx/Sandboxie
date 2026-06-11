---
kind: srev-ledger-entry
id: SREV-310
title: Key ZoneMap Domains Short-Circuit
status: patched source-level after official registry enumeration and local filewire shape; needs Windows runtime proof
owner: Sandboxie/core/dll/key_merge.c
spec: docs/plan/srev-310-key-zonemap-domains-short-circuit.md
schema: docs/plan/srev-310-key-zonemap-domains-short-circuit.schema.json
checker: docs/plan/check-srev-310.py
runtime_gate: Windows ZoneMap Domains registry smoke plus service-status and allocation-failure controls
---

### SREV-310: Key ZoneMap Domains Short-Circuit

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | patched source-level after official registry enumeration and local filewire shape; needs Windows runtime proof |
| Evidence | `Key_ShouldNotMerge` short-circuits merge for HKLM/HKCU `Software\Microsoft\Windows\CurrentVersion\Internet Settings\ZoneMap\Domains` when SbieSvc proves the sandbox copy key is absent. The old comment called this a `hack` for large SpyBot S&D Immunize-created subkey trees and Adobe Reader X brokered `NtOpenKey` behavior. The branch built `FILE_CHECK_KEY_EXISTS_REQ` and wrote request fields immediately after `Dll_AllocTemp(req_len)` without checking allocation success. |
| Data | `Key_ShouldNotMerge`, `Key_Merge`, `TruePath`, `CopyPath`, `Key_System`, `Key_CurrentUser`, `_Domains`, `HaveHklmDomainsKey`, `HaveHkcuDomainsKey`, `FILE_CHECK_KEY_EXISTS_REQ`, `MSGID_FILE_CHECK_KEY_EXISTS`, `SbieDll_CallServer`, `STATUS_OBJECT_NAME_NOT_FOUND`, `STATUS_OBJECT_PATH_NOT_FOUND`, SbieSvc `FileServer::CheckKeyExists`, and SREV-033. |
| Schema | `KEY_ZONEMAP_DOMAINS_SHORT_CIRCUIT` says `Key_ShouldNotMerge` owns only the ZoneMap Domains merge short-circuit decision; `ZwEnumerateKey` and `KEY_NODE_INFORMATION` define host registry subkey enumeration shape; SREV-033 owns `FILE_CHECK_KEY_EXISTS_REQ` byte-counted wire string shape; only SbieSvc object-not-found or path-not-found status proves sandbox Domains copy-key absence for short-circuiting; allocation failure must preserve normal merge behavior. |
| Topology | `Key_Merge -> Key_ShouldNotMerge -> HKLM/HKCU ZoneMap Domains predicate -> FILE_CHECK_KEY_EXISTS_REQ allocation -> SbieSvc CheckKeyExists -> object/path-not-found -> cache absence -> short-circuit merge`. Allocation failure returns `FALSE` so `Key_Merge` keeps normal merge behavior. Other service statuses also preserve normal merge. |
| Logic Risk | The optimization must not treat an unproven box-key absence as proven. An unchecked allocation could crash before SbieSvc can answer, and a failed probe must not become a short-circuit. The safe failure mode is normal merge, even if slower. |
| Official Shape | Microsoft documents `ZwEnumerateKey` as returning information about a subkey by index from an open registry key, with `ResultLength` reporting returned or required bytes. Microsoft documents `KEY_NODE_INFORMATION` as the `KeyNodeInformation` buffer shape, including counted non-null-terminated key names and `LastWriteTime`. |
| Fix | The source comment now names SREV-310, the ZoneMap Domains short-circuit owner, the SbieSvc box-key existence probe, the Adobe Reader broker reason, and the fail-open-to-normal-merge rule. `Key_ShouldNotMerge` now checks `Dll_AllocTemp(req_len)` before request writes and returns `FALSE` on allocation failure. No Domains path predicate, HKLM/HKCU split, wire request layout, service message id, SbieSvc status interpretation, or successful short-circuit behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-310.py` validates the draft-07 schema, official references, source comment owner, allocation gate before request writes, unchanged Domains predicates and `FILE_CHECK_KEY_EXISTS_REQ` wire shape, SREV-033 adjacency, stale `hack` wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-310.sh` is the targeted wrapper. Runtime gate: Windows ZoneMap Domains registry smoke plus service-status and allocation-failure controls. |
