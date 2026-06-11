---
kind: srev-ledger-entry
id: SREV-311
title: Key Rule Dummy LastWrite Owner
status: patched source-level after official ZwQueryKey and KEY_NODE_INFORMATION shape; needs Windows runtime proof
owner: Sandboxie/core/dll/key_merge.c
spec: docs/plan/srev-311-key-rule-dummy-lastwrite-owner.md
schema: docs/plan/srev-311-key-rule-dummy-lastwrite-owner.schema.json
checker: docs/plan/check-srev-311.py
runtime_gate: Windows rule-specificity registry enumeration smoke plus query-failure fallback injection
---

### SREV-311: Key Rule Dummy LastWrite Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official `ZwQueryKey` and `KEY_NODE_INFORMATION` shape; needs Windows runtime proof |
| Evidence | `Key_MergeCacheDummys` builds rule-derived dummy subkeys when rule specificity is enabled and the parent true key is not directly enumerable. It probes each candidate `FakePath` with `SbieApi_OpenKey`, inserts a `KEY_MERGE_SUBKEY` when the open succeeds, and formerly set `subkey->LastWriteTime.QuadPart = 0` with a `todo: fix-me` comment. That metadata can flow to `Key_NtEnumerateKeyFake` output. |
| Data | `Key_MergeCacheDummys`, `SbieDll_GetReadablePaths`, `Pattern_Source`, `TruePath`, `FakePath`, `SbieApi_OpenKey`, `__sys_NtQueryKey`, `KeyBasicInformation`, `KEY_BASIC_INFORMATION.LastWriteTime`, `KEY_MERGE_SUBKEY.LastWriteTime`, `TitleOrClass`, `Key_NtEnumerateKeyFake`, `KEY_NODE_INFORMATION`, and `KEY_INFORMATION_CLASS`. |
| Schema | `KEY_RULE_DUMMY_LASTWRITE_OWNER` says `Key_MergeCacheDummys` owns metadata for rule-derived dummy subkeys; `ZwQueryKey` with `KeyBasicInformation` can return `LastWriteTime` for an open key handle; `KEY_NODE_INFORMATION.LastWriteTime` is caller-visible registry subkey metadata; query failure must preserve dummy subkey visibility with the existing zero fallback; this SREV does not change rule inclusion or merge ordering. |
| Topology | `readable key path rule -> Key_MergeCacheDummys -> FakePath -> SbieApi_OpenKey -> ZwQueryKey(KeyBasicInformation) -> KEY_MERGE_SUBKEY.LastWriteTime -> Key_NtEnumerateKeyFake caller-visible metadata if fake route is needed`. Query failure keeps the dummy subkey and uses the zero fallback. |
| Logic Risk | Zero `LastWriteTime` was a less faithful metadata fallback even when the code already held an open key handle. Removing the dummy subkey on query failure would be worse because rule-visible subkey inclusion was already proven by `SbieApi_OpenKey`; only metadata precision failed. |
| Official Shape | Microsoft documents `KEY_NODE_INFORMATION.LastWriteTime` as the last time the key or one of its values changed, in absolute system time. Microsoft documents `ZwQueryKey` as returning key information for an open key handle, and `KEY_INFORMATION_CLASS` as the selector for `KeyBasicInformation`, `KeyNodeInformation`, and related query/enumeration shapes. |
| Fix | `Key_MergeCacheDummys` now calls `__sys_NtQueryKey(KeyBasicInformation)` on the successfully opened `FakePath` handle before closing it. If the query succeeds or returns `STATUS_BUFFER_OVERFLOW`, it copies `info.LastWriteTime` into the dummy `KEY_MERGE_SUBKEY`; otherwise it preserves the old zero fallback. No readable-path scan, path-component extraction, duplicate suppression, sorted insert order, `TitleOrClass`, or dummy-subkey inclusion behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-311.py` validates the draft-07 schema, official references, source `ZwQueryKey` owner, query-before-close ordering, zero fallback only after query failure, stale TODO removal, unchanged rule-specificity path scan and duplicate suppression, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-311.sh` is the targeted wrapper. Runtime gate: Windows rule-specificity registry enumeration smoke plus query-failure fallback injection. |
