---
kind: srev-ledger-entry
id: SREV-325
title: Secure Elevation Flags Fake Admin Allowlist
status: comment-classified-after-official-uac-and-token-elevation-shape-review-no-behavior-change
owner: Sandboxie/core/dll/secure.c
spec: docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.md
schema: docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.schema.json
checker: docs/plan/check-srev-325.py
runtime_gate: IE Protected Mode / ActiveX install broker smoke, SbieSvc UAC elevator smoke, SandboxieRpcSs elevated COM smoke, Synaptics compatibility smoke if available, and negative control proving non-allowlisted callers still forward to native RtlQueryElevationFlags
---
### SREV-325: Secure Elevation Flags Fake Admin Allowlist

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | comment classified after official UAC and token elevation shape review; no source behavior change |
| Evidence | `Secure_Init` resolves `RtlQueryElevationFlags`, installs `Secure_RtlQueryElevationFlags`, then sets `Secure_ShouldFakeRunningAsAdmin` for SbieSvc, SandboxieRpcSs, Internet Explorer, `SynTPEnh.exe`, and `SynTPHelper.exe`. `Secure_RtlQueryElevationFlags` owns the transition: it may return `Flags = 0` / `STATUS_SUCCESS` for `Secure_FakeAdmin`, `proc_create_process_fake_admin`, selected IE paths, SbieSvc during create-process, or the generic broker/Synaptics path; otherwise it forwards to `__sys_RtlQueryElevationFlags`. |
| Data | `RtlQueryElevationFlags`, `Secure_ShouldFakeRunningAsAdmin`, `Secure_RtlQueryElevationFlags`, `Secure_FakeAdmin`, `proc_create_process_fake_admin`, `DLL_IMAGE_SANDBOXIE_SBIESVC`, `DLL_IMAGE_SANDBOXIE_RPCSS`, `DLL_IMAGE_INTERNET_EXPLORER`, `Secure_IsInternetExplorerTabProcess`, `SH_GetInternetExplorerVersion`, `SBIE_FLAG_RIGHTS_DROPPED`, `SynTPEnh.exe`, `SynTPHelper.exe`, `Flags = 0`, `STATUS_SUCCESS`, and `__sys_RtlQueryElevationFlags`. |
| Schema | `SECURE_ELEVATION_FLAGS_FAKE_ADMIN_ALLOWLIST` says official UAC/token documentation owns elevation semantics; `RtlQueryElevationFlags` is a local observed ntdll hook target, not a public Microsoft Win32 schema in this SREV; `Secure_Init` owns only the process/image allowlist for the hook; `Secure_RtlQueryElevationFlags` owns the local decision to return zero flags or forward to native; IE Protected Mode registry fake values remain owned by SREV-307 / `key.c`; this SREV changes comments and proof only. |
| Topology | `Secure_Init -> resolve RtlQueryElevationFlags -> install Secure_RtlQueryElevationFlags hook -> set Secure_ShouldFakeRunningAsAdmin allowlist`. Runtime query path is `caller queries elevation flags -> Secure_RtlQueryElevationFlags -> Secure_FakeAdmin / proc_create_process_fake_admin / allowlist sub-gate -> zero Flags + STATUS_SUCCESS -> otherwise __sys_RtlQueryElevationFlags`. |
| Logic Risk | The old `$Workaround$ - 3rd party fix` label hid the actual local contract: this is not a broad third-party bypass, but an allowlist for one hook's zero-flag faking behavior. Future changes must not add images to this list without naming whether the caller is an IE Protected Mode path, SbieSvc UAC elevator path, RpcSs broker path, or another caller with a Windows runtime compatibility gate. |
| Official Shape | `docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.md` records Microsoft UAC architecture, UAC behavior, `TOKEN_INFORMATION_CLASS`, and `TOKEN_ELEVATION_TYPE` references. It also records that no public Microsoft Win32 API page was found for `RtlQueryElevationFlags` during this pass. `docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.schema.json` records the JSON Schema draft-07 local `SECURE_ELEVATION_FLAGS_FAKE_ADMIN_ALLOWLIST` contract. |
| Fix | Comment-only source clarification. The source now names SREV-325 and says the allowlist feeds `RtlQueryElevationFlags` zero-flag faking for IE, SbieSvc/RpcSs brokers, and Synaptics callers. No hook installation, image predicate, `Secure_ShouldFakeRunningAsAdmin` assignment, `Secure_RtlQueryElevationFlags` branch, returned flag value, status, or native forwarding behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-325.py` validates the draft-07 schema, official references, source comment, preserved allowlist, preserved IE sub-gates, preserved SbieSvc create-process gate, preserved generic broker/Synaptics fake path, native forwarding fallback, SREV-307 adjacency, stale workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-325.sh` is the targeted wrapper. Windows gate: IE Protected Mode / ActiveX install broker smoke, SbieSvc UAC elevator smoke, SandboxieRpcSs elevated COM smoke, Synaptics compatibility smoke if available, and negative control proving non-allowlisted callers still forward to native `RtlQueryElevationFlags`. |
