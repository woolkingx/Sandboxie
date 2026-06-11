---
kind: srev-ledger-entry
id: SREV-309
title: Key Save Merge Materialization Boundary
status: source-level classified after official registry save and enumeration shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-309-key-save-merge-materialization-boundary.md
schema: docs/plan/srev-309-key-save-merge-materialization-boundary.schema.json
checker: docs/plan/check-srev-309.py
runtime_gate: Windows hive-save smoke covering host-only, box-only, deleted, relocated, typed value, and NtSaveKeyEx flag cases before any materialization change
---

### SREV-309: Key Save Merge Materialization Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official registry save and enumeration shape; comment-only source clarification, no behavior change |
| Evidence | `Key_NtSaveKey` and `Key_NtSaveKeyEx` currently log `MSG_2205` and call `__sys_NtSaveKey` / `__sys_NtSaveKeyEx` directly. The old comments said to copy all registry keys from host to box for the used `KeyHandle` so everything would be saved. That describes a real topology gap: Sandboxie exposes a merged host+box registry view through `Key_Merge`, enumeration, and query helpers, while native save persists the physical tree behind the handle. |
| Data | `Key_NtSaveKey`, `Key_NtSaveKeyEx`, `KeyHandle`, `FileHandle`, `Flags`, `SbieApi_Log(2205)`, `__sys_NtSaveKey`, `__sys_NtSaveKeyEx`, `Key_GetName`, `TruePath`, `CopyPath`, `Key_Merge`, `Key_NtEnumerateKey`, `Key_NtEnumerateValueKey`, `Key_NtQueryValueKey`, delete markers, and relocation state. |
| Schema | `KEY_SAVE_MERGE_MATERIALIZATION_BOUNDARY` says `Key_NtSaveKey` and `Key_NtSaveKeyEx` currently delegate to native save of the physical key tree behind `KeyHandle`; `RegSaveKey` and `RegSaveKeyEx` save a specified key plus subkeys and values to a registry file; `Key_Merge` owns virtual host+box registry enumeration and query semantics; pre-save materialization is a separate registry-copy topology requiring Windows hive-save runtime proof; this SREV changes comments and proof only. |
| Topology | Current save topology is `caller KeyHandle -> Key_NtSaveKey / Key_NtSaveKeyEx -> native save -> physical registry tree behind KeyHandle`. Sandboxie's merged-read topology is `KeyHandle -> Key_GetName -> TruePath + CopyPath -> Key_Merge -> merged subkey/value enumeration/query`. Future materialization would need to enumerate merged nodes, create/copy missing host-only nodes into the box tree, preserve delete/relocation semantics, and then save the materialized tree. |
| Logic Risk | The old TODO describes a solution without naming owner, API shape, or proof. Copying all registry keys before save crosses merge semantics, delete markers, relocation, value type/data copying, security descriptors, virtualization policy, and native hive-save file ownership. This cannot be treated as a local one-line fix. |
| Official Shape | Microsoft documents `RegSaveKeyW` as saving a specified key and all its subkeys and values to a new file. Microsoft documents `RegSaveKeyEx` as the extended save operation with a format `Flags` parameter. Microsoft documents `ZwEnumerateKey`, `ZwEnumerateValueKey`, and `ZwQueryValueKey` as separate enumeration/query surfaces that a future materializer would need to drive or emulate. |
| Fix | The source comments now name SREV-309 and the physical-tree boundary for `NtSaveKey` and `NtSaveKeyEx`. They explicitly state that the merged host+box view is not materialized before native save, and that pre-save materialization requires a Windows hive-save runtime gate before behavior changes. No log call, native save call, or `NtSaveKeyEx` flag forwarding changed. |
| Acceptance Gate | `docs/plan/check-srev-309.py` validates the draft-07 schema, official references, source comment owner, unchanged native save calls, merge/enumeration adjacency, stale TODO removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-309.sh` is the targeted wrapper. Runtime gate: Windows hive-save smoke covering host-only, box-only, deleted, relocated, typed value, and `NtSaveKeyEx` flag cases before any materialization behavior change. |
