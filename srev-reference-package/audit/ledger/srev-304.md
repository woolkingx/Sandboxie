---
kind: srev-ledger-entry
id: SREV-304
title: Key TrustedInstaller StoreDirty Policy Boundary
status: source-level classified after official ZwSetValueKey shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-304-key-trustedinstaller-storedirty-policy-boundary.md
schema: docs/plan/srev-304-key-trustedinstaller-storedirty-policy-boundary.schema.json
checker: docs/plan/check-srev-304.py
runtime_gate: Windows TrustedInstaller WinSxS assembly install smoke plus negative StoreDirty controls before any predicate change
---

### SREV-304: Key TrustedInstaller StoreDirty Policy Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official `ZwSetValueKey` shape; comment-only source clarification, no behavior change |
| Evidence | `Key_NtSetValueKey` normalizes `ValueName` into a counted `UNICODE_STRING` view. For `DLL_IMAGE_TRUSTED_INSTALLER` and counted value name `StoreDirty`, it returns `STATUS_SUCCESS` before calling the native setter. The old comment described WinSxS assembly install behavior but used workaround/complaint wording and did not name the registry API owner, counted-name boundary, or runtime gate for any future predicate change. |
| Data | `Key_NtSetValueKey`, `ValueName`, `UNICODE_STRING`, `DLL_IMAGE_TRUSTED_INSTALLER`, `StoreDirty`, `STATUS_SUCCESS`, `__sys_NtSetValueKey`, `NtOpenKey(KEY_WRITE)`, `\REGISTRY\MACHINE\COMPONENTS`, and SREV-213. |
| Schema | `KEY_TRUSTEDINSTALLER_STOREDIRTY_POLICY_BOUNDARY` says `Key_NtSetValueKey` owns only the TrustedInstaller StoreDirty compatibility suppression branch; `ZwSetValueKey` owns registry value create-or-replace behavior; `ValueName` is a counted `UNICODE_STRING` value-name input; SREV-213 owns adjacent counted registry value-name handling; this SREV changes comments and proof only. |
| Topology | `NtSetValueKey caller -> Key_NtSetValueKey -> counted ValueName normalization -> TrustedInstaller StoreDirty policy branch -> STATUS_SUCCESS suppression`; non-matching writes continue to `__sys_NtSetValueKey` and the existing access-denied reopen path. |
| Logic Risk | Generic workaround wording makes this branch look like an arbitrary registry write skip. The actual boundary is narrower: TrustedInstaller image, StoreDirty value name, and WinSxS COMPONENTS runtime compatibility. Because the current source does not prove key path, type, or data shape at this branch, predicate changes require Windows runtime evidence. |
| Official Shape | Microsoft documents `ZwSetValueKey` as creating or replacing a registry value entry, with `ValueName` supplied as a `PUNICODE_STRING`; if no matching value exists, the routine creates a new entry, and if one exists it replaces it. Microsoft documents registry value types as the type tags used when storing value data. |
| Fix | The source comment now names SREV-304, `ZwSetValueKey` create/replace behavior, the deliberate TrustedInstaller/WinSxS policy boundary, and the Windows runtime gate for any future predicate change. No TrustedInstaller image check, 10-WCHAR counted `StoreDirty` match, returned `STATUS_SUCCESS`, normal `__sys_NtSetValueKey` path, or access-denied reopen path changed. |
| Acceptance Gate | `docs/plan/check-srev-304.py` validates the draft-07 schema, official references, source comment owner, unchanged StoreDirty predicate, unchanged normal `__sys_NtSetValueKey` path, SREV-213 adjacency, stale workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-304.sh` is the targeted wrapper. Runtime gate: Windows TrustedInstaller/WinSxS assembly install smoke plus negative controls for non-TrustedInstaller callers and non-COMPONENTS StoreDirty writes before any predicate change. |
