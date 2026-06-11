---
kind: srev-ledger-entry
id: SREV-317
title: Ldr Third-Party Module Callback Group
status: patched comment/topology for non-Microsoft loader callback group; no behavior change
owner: Sandboxie/core/dll/ldr.c
spec: docs/plan/srev-317-ldr-third-party-module-callback-group.md
schema: docs/plan/srev-317-ldr-third-party-module-callback-group.schema.json
checker: docs/plan/check-srev-317.py
runtime_gate: No runtime gate for this comment-only group-label clarification; future behavior changes inherit the affected callback owner's Windows gate
---

### SREV-317: Ldr Third-Party Module Callback Group

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology for non-Microsoft loader callback group; no behavior change |
| Evidence | `Ldr_Dlls` maps loaded DLL base names to init callbacks. The non-Microsoft group registers `acscmonitor.dll -> Acscmonitor_Init`, `IDMIECC.dll -> Custom_InternetDownloadManager`, `snxhk.dll/snxhk64.dll -> Custom_Avast_SnxHk`, `sysfer.dll -> Custom_SYSFER_DLL`, and architecture-specific `dgapi64.dll/dgapi.dll -> DigitalGuardian_Init`. The old group header called the whole block `$Workaround$ - 3rd party fix`, which made unrelated callback owners look like one shared policy. |
| Data | `Ldr_Dlls`, `acscmonitor.dll`, `IDMIECC.dll`, `snxhk.dll`, `snxhk64.dll`, `sysfer.dll`, `dgapi64.dll`, `dgapi.dll`, `Acscmonitor_Init`, `Custom_InternetDownloadManager`, `Custom_Avast_SnxHk`, `Custom_SYSFER_DLL`, `DigitalGuardian_Init`, `_M_ARM64`, `_WIN64`, SREV-259, SREV-257, SREV-055, SREV-258, SREV-088, and SREV-249. |
| Schema | `LDR_THIRD_PARTY_MODULE_CALLBACK_GROUP` says `Ldr_Dlls` owns only loaded module base-name to init-callback registration; the non-Microsoft group label must not imply one shared vendor behavior owner; `Acscmonitor_Init` behavior remains owned by `CUSTOM_ACSCMONITOR_LOADER_REFERENCE`; `Custom_Avast_SnxHk` behavior remains owned by `CUSTOM_AVAST_TRAMPOLINE_PUBLISH_GATE`; `Custom_SYSFER_DLL` behavior remains owned by `CUSTOM_SYSFER_ENTRYPOINT_PATCH` and `CUSTOM_SYSFER_COMMENT_OWNER`; `DigitalGuardian_Init` behavior remains owned by `DLL_DIGITALGUARDIAN_MODULE_FLAG` and `DIGITALGUARDIAN_COMMENT_TOPOLOGY`; this SREV changes the loader group comment only, not DLL names, callbacks, architecture guards, or return values. |
| Topology | `Windows loader observes a loaded module -> Ldr_Dlls base-name match -> owner-specific init callback -> vendor-specific compatibility owner`. Group topology: `non-Microsoft module callback group -> ARM64 excludes acscmonitor / IDMIECC / snxhk / sysfer callbacks -> architecture-specific Digital Guardian callback remains dgapi64/dgapi -> callback body owns behavior, not the group header`. |
| Logic Risk | The generic header hid that the group entries have different owners: loader reference lifetime, executable trampoline publication, PE entry-point patching, and module-presence flagging. Future edits must follow the entry-specific SREV instead of treating the whole group as one third-party policy. |
| Official Shape | Microsoft documents `LoadLibraryW` as loading modules into the calling process with per-process module handles and reference counts. Microsoft documents `GetModuleHandleW` as returning a handle for an already-loaded module without incrementing the reference count. |
| Fix | `ldr.c` now labels the block as the SREV-317 non-Microsoft module callback registration group. No DLL name, callback function, ARM64 guard, architecture-specific Digital Guardian selection, callback body, or return value changed. |
| Acceptance Gate | `docs/plan/check-srev-317.py` validates the draft-07 schema, official references, loader group label, exact DLL-to-callback registrations, ARM64 guard, Digital Guardian architecture split, adjacent SREV owner references, stale generic workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-317.sh` is the targeted wrapper. Runtime gate: no runtime gate is required for this comment-only group-label clarification. Any future behavior change must run the owner-specific runtime gate for the affected callback, such as the ActivClient, Avast/SnxHk, SYSFER, or Digital Guardian gates named by the adjacent SREVs. |
