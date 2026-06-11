---
kind: srev-ledger-entry
id: SREV-321
title: Proc MSI Systemless Process Gate
status: comment-classified-after-official-process-token-and-msi-service-shape-review-no-behavior-change
owner: Sandboxie/core/dll/proc.c
spec: docs/plan/srev-321-proc-msi-systemless-process-gate.md
schema: docs/plan/srev-321-proc-msi-systemless-process-gate.schema.json
checker: docs/plan/check-srev-321.py
runtime_gate: Windows MSI install/repair/custom-action smoke with systemless MSIServer, RunServicesAsSystem negative smoke, MsiInstallerExemptions negative smoke, and SREV-092/SREV-270 regressions
---
### SREV-321: Proc MSI Systemless Process Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | comment classified after official process-token and MSI service shape review; no source behavior change |
| Evidence | `Proc_CreateProcessInternalW` has a direct-create branch for compartment mode or `OriginalToken`. Inside it, `DLL_IMAGE_MSI_INSTALLER && Scm_MsiServer_Systemless && !RunServicesAsSystem && !MsiInstallerExemptions` clears `hToken` and `lpProcessAttributes` before calling `__sys_CreateProcessInternalW`. The old source comment called this a simple MSI workaround. |
| Data | `Proc_CreateProcessInternalW`, `Dll_CompartmentMode`, `OriginalToken`, `DLL_IMAGE_MSI_INSTALLER`, `Scm_MsiServer_Systemless`, `RunServicesAsSystem`, `MsiInstallerExemptions`, `hToken`, `lpProcessAttributes`, `__sys_CreateProcessInternalW`, and `Scm_SetupMsiHooks`. |
| Schema | `PROC_MSI_SYSTEMLESS_PROCESS_GATE` says MSI systemless state is owned by `scm_msi.c`; process creation token/security-attributes selection is owned by this `proc.c` branch; the branch is legal only for `DLL_IMAGE_MSI_INSTALLER`, `Scm_MsiServer_Systemless`, not `RunServicesAsSystem`, and not `MsiInstallerExemptions`; clearing `hToken` and `lpProcessAttributes` must stay local to that exact predicate; SREV-092 owns MSI in-use event lifetime; SREV-270 owns the Config.Msi file retry; this SREV changes comments and proof only. |
| Topology | `MSI process creation request -> Proc_CreateProcessInternalW direct-create branch -> systemless MSI predicate -> hToken/lpProcessAttributes preserved or cleared -> __sys_CreateProcessInternalW`. Adjacent MSI topology remains `scm_msi.c -> Scm_SetupMsiHooks -> Scm_MsiServer_Systemless`, `scm_msi.c -> Scm_MsiDll -> MSI in-use event lifetime (SREV-092)`, and `file.c -> Config.Msi directory retry (SREV-270)`. |
| Logic Risk | Anonymous workaround wording hides the security boundary: this branch changes process creation token and process-security attributes for a narrow systemless MSI server condition. Future edits should not broaden or remove the predicate without Windows MSI runtime proof. |
| Official Shape | `docs/plan/srev-321-proc-msi-systemless-process-gate.md` records Microsoft `CreateProcessW`, `CreateProcessAsUserW`, access token, and Windows Installer service references. `docs/plan/srev-321-proc-msi-systemless-process-gate.schema.json` records the JSON Schema draft-07 local `PROC_MSI_SYSTEMLESS_PROCESS_GATE` contract. |
| Fix | Comment-only source clarification. The source now names the branch as the SREV-321 systemless MSI server child process creation gate and records that the existing predicate is the only scope for clearing `hToken` and `lpProcessAttributes`. No token value, process-attributes value, predicate, direct-create call, MSI hook state, in-use event, or Config.Msi file behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-321.py` validates the draft-07 schema, official references, source comment, preserved MSI systemless predicate, preserved `hToken` and `lpProcessAttributes` assignments, stale workaround wording removal from this branch, SREV-092/SREV-270 adjacency, and split ledger fragment; `docs/plan/check-srev-321.sh` is the targeted wrapper. Windows gate: MSI install/repair/custom-action smoke with systemless MSIServer, `RunServicesAsSystem` negative smoke, `MsiInstallerExemptions` negative smoke, and regression checks for SREV-092 MSI lifetime plus SREV-270 Config.Msi retry. |
