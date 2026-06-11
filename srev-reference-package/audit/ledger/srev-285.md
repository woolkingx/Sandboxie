---
kind: srev-ledger-entry
id: SREV-285
title: MSO Recovery Module Signal Owner
status: patched-comment-topology-after-official-dll-module-review-no-behavior-change
owner: Sandboxie/core/dll/file_recovery.c
additional_owners:
  - Sandboxie/core/dll/ldr.c
spec: docs/plan/srev-285-mso-recovery-module-signal-owner.md
schema: docs/plan/srev-285-mso-recovery-module-signal-owner.schema.json
checker: docs/plan/check-srev-285.py
runtime_gate: Windows Office recovery matrix with mso-loaded and mso-not-loaded processes, Office temp names, RecoverFolder, AutoRecoverIgnore, and SREV-072 redirector normalization
---

### SREV-285: MSO Recovery Module Signal Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official DLL module review; no behavior change |
| Evidence | `ldr.c` registers `File_MsoDll` for `mso.dll`. `File_MsoDll` sets `File_MsoDllLoaded = TRUE`. `File_IsRecoverable` uses that flag to ignore Microsoft Office temporary names beginning with `~$` and extensionless temporary names after a `RecoverFolder` match. The old comments called this a hack instead of naming the module-presence signal and recovery owner. |
| Data | `mso.dll`, loader module callback table, `File_MsoDll`, `File_MsoDllLoaded`, `File_IsRecoverable`, `RecoverFolder`, `AutoRecoverIgnore`, Office `~$` temporary-name filter, extensionless-name filter, and SREV-072. |
| Schema | `MSO_RECOVERY_MODULE_SIGNAL_OWNER` says DLL load state is process-local module presence; the `mso.dll` callback publishes only `File_MsoDllLoaded`; `File_MsoDllLoaded` is a module-presence signal for the Office recovery filter; `File_IsRecoverable` owns the Office temporary-file recovery classification; Office temporary-file filtering applies only after `RecoverFolder` prefix match; SREV-072 owns recoverable-path redirector normalization; this SREV changes comments and proof only. |
| Topology | `mso.dll loaded -> ldr.c module callback table -> File_MsoDll -> File_MsoDllLoaded = TRUE`. `File_IsRecoverable -> RecoverFolder prefix match -> if File_MsoDllLoaded, Office temp-file filter -> AutoRecoverIgnore checks`. |
| Logic Risk | Generic hack wording can make this callback look like removable module-table noise or encourage moving Office temporary-name filtering into generic recovery behavior. The actual owner boundary is a module-presence signal feeding an Office-specific classification step. |
| Official Shape | Microsoft documents dynamic-link library functions including `LoadLibrary`, which maps an executable module into the calling process address space, and module-handle APIs for loaded modules. This SREV uses that official shape only to classify `mso.dll` as process-local module presence; recovery classification remains local Sandboxie policy. |
| Fix | Comment-only source clarification. The loader table and callback now name SREV-285 and describe `mso.dll` as the module-presence signal for the Office recovery filter. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-285.py` validates the draft-07 schema, official reference, loader callback registration, `File_MsoDllLoaded` flag, Office filter use inside `File_IsRecoverable`, SREV-072 adjacency, stale source wording removal, and ledger fragment; `docs/plan/check-srev-285.sh` is the targeted wrapper. Runtime gate: Windows Office recovery matrix covering mso-loaded and mso-not-loaded processes, recoverable Office documents, `~$` temporary names, extensionless temporary names, configured `RecoverFolder`, configured `AutoRecoverIgnore`, and SREV-072 network redirector normalization. |
