---
kind: srev-ledger-entry
id: SREV-308
title: Key CreateProcess SRP Authenticode Owner
status: source-level classified after official ZwQueryValueKey, KEY_VALUE_PARTIAL_INFORMATION, CreateProcessW, and SRP certificate-rule shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-308-key-createprocess-srp-authenticode-owner.md
schema: docs/plan/srev-308-key-createprocess-srp-authenticode-owner.schema.json
checker: docs/plan/check-srev-308.py
runtime_gate: Windows process-creation smoke with SRP/AppLocker certificate-rule policy enabled plus SandboxieCrypto/SandboxieRpcSs startup proof before any predicate change
---

### SREV-308: Key CreateProcess SRP Authenticode Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official `ZwQueryValueKey`, `KEY_VALUE_PARTIAL_INFORMATION`, `CreateProcessW`, and SRP certificate-rule shape; comment-only source clarification, no behavior change |
| Evidence | `Key_NtQueryValueKey` calls `Key_NtQueryValueKeyFakeForCreateProcess` only from the `KeyValuePartialInformation` fake-value gate while `TlsData->proc_create_process` is set. The fake owner fabricates exactly one `REG_DWORD` value: counted name `AuthenticodeEnabled` returns `0`; non-matches return `STATUS_BAD_INITIAL_PC`. The old comment named the recursive `SandboxieCrypto` / `SandboxieRpcSs` hang symptom but did not name the SRP certificate-rule API shape or adjacent SRP/AppLocker topology. |
| Data | `Key_NtQueryValueKey`, `Key_NtQueryValueKeyFakeForCreateProcess`, `TlsData->proc_create_process`, `AuthenticodeEnabled`, `REG_DWORD`, `KEY_VALUE_PARTIAL_INFORMATION`, `STATUS_SUCCESS`, `STATUS_BAD_INITIAL_PC`, `SandboxieCrypto`, `SandboxieRpcSs`, `AdvApi_EnableDisableSRP`, `SaferComputeTokenFromLevel`, `Token_Restrict`, and `SANDBOX_INERT`. |
| Schema | `KEY_CREATEPROCESS_SRP_AUTHENTICODE_OWNER` says `Key_NtQueryValueKeyFakeForCreateProcess` owns only the CreateProcess-time `AuthenticodeEnabled` `REG_DWORD` fake value; `ZwQueryValueKey` owns caller buffer and result-length contract; `KEY_VALUE_PARTIAL_INFORMATION` requires `Type`, `DataLength`, and counted `Data`; SRP certificate rules process Authenticode-signed EXE launch and may trigger CRL checks; this SREV changes comments and proof only. |
| Topology | `CreateProcess -> TlsData->proc_create_process -> SRP certificate-rule registry query -> Key_NtQueryValueKeyFakeForCreateProcess -> synthetic REG_DWORD 0 KEY_VALUE_PARTIAL_INFORMATION -> avoid recursive SandboxieCrypto startup during SandboxieRpcSs loading`; non-matches continue to normal registry merge/query handling. |
| Logic Risk | The old comment focused on the hang symptom. The stable boundary is CreateProcess-time SRP certificate-rule query, exact `AuthenticodeEnabled` value name, complete DWORD partial-information payload, and otherwise unchanged fall-through. Future changes require Windows runtime proof under SRP/AppLocker and SandboxieCrypto/SandboxieRpcSs startup. |
| Official Shape | Microsoft documents `CreateProcessW` as creating a new process and primary thread in the caller's security context. Microsoft documents Software Restriction Policies as Group Policy-driven trust policies controlling whether software can run, and names Authenticode and WinVerifyTrust APIs as components used to process signed executable files. Microsoft documents the certificate-rules setting as processing digital certificates when SRP is enabled and a user/process attempts to run an `.exe`, and notes certificate rules check CRLs for signed program startup. Microsoft documents the `ZwQueryValueKey` and `KEY_VALUE_PARTIAL_INFORMATION` buffer shape. |
| Fix | The source comment now names SREV-308, the CreateProcess-time SRP certificate-rule boundary, Microsoft's Authenticode/CRL processing shape for signed executable launch, and the local reason for keeping this exact fake value disabled during Sandboxie process creation. No dispatcher, value predicate, payload, status, or normal registry path changed. |
| Acceptance Gate | `docs/plan/check-srev-308.py` validates the draft-07 schema, official references, source comment owner, unchanged `TlsData->proc_create_process` dispatch, unchanged `AuthenticodeEnabled` predicate, unchanged `KEY_VALUE_PARTIAL_INFORMATION` payload construction, adjacent SRP/AppLocker topology evidence, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-308.sh` is the targeted wrapper. Runtime gate: Windows process-creation smoke with SRP/AppLocker certificate-rule policy enabled plus SandboxieCrypto/SandboxieRpcSs startup proof before any predicate change. |
