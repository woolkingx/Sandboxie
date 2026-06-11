---
kind: srev-ledger-entry
id: SREV-282
title: Chrome Flash Volume-Info Dormant Hook
status: patched-comment-topology-after-official-getvolumeinformation-review-no-behavior-change
owner: Sandboxie/core/dll/file_init.c
additional_owners:
  - Sandboxie/core/dll/file_misc.c
spec: docs/plan/srev-282-chrome-flash-volume-info-dormant-hook.md
schema: docs/plan/srev-282-chrome-flash-volume-info-dormant-hook.schema.json
checker: docs/plan/check-srev-282.py
runtime_gate: None for dormant hook state; future revival requires Windows caller proof and volume-info regression matrix
---

### SREV-282: Chrome Flash Volume-Info Dormant Hook

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `GetVolumeInformationW` review; no behavior change |
| Evidence | `file_init.c` contains a commented-out `GetProcAddress("GetVolumeInformationW")` plus commented-out `SBIEDLL_HOOK(File_,GetVolumeInformationW)`. `file_misc.c` contains the matching commented-out `File_GetVolumeInformationW` body for a Chrome all-null output-parameter probe. The old comments used workaround wording even though the registration and body are inactive. |
| Data | `GetVolumeInformationW`, commented `File_GetVolumeInformationW`, commented `SBIEDLL_HOOK(File_,GetVolumeInformationW)`, `Dll_ChromeSandbox`, all-null output-parameter predicate, `__sys_GetVolumeInformationW`, SREV-273, and SREV-279. |
| Schema | `CHROME_FLASH_VOLUME_INFO_DORMANT_HOOK` says `GetVolumeInformationW` retrieves file-system and volume information for a root directory; `lpRootPathName` may be NULL and then uses the current directory root; output pointers are optional; buffer sizes are ignored when the corresponding output buffer is absent; the Chrome Flash `GetVolumeInformationW` hook registration remains inactive; the Chrome Flash all-null predicate body remains inactive; future revival requires Windows proof and a current caller contract; SREV-273 and SREV-279 own active adjacent volume-info behavior; this SREV changes comments and proof only. |
| Topology | `file_init.c commented GetVolumeInformationW registration -> no active hook`. `file_misc.c commented File_GetVolumeInformationW body -> no current runtime edge`. Active adjacent volume-info behavior remains with final-path volume-name owner SREV-273, native volume-info owner SREV-279, and by-handle Win32 volume-info hook code. |
| Logic Risk | Broad workaround wording around inactive code can drive re-enabling an old app-specific hook without current caller proof. Since Microsoft permits NULL `lpRootPathName` and optional output pointers, the all-null output-parameter shape alone is not a current Sandboxie policy or compatibility contract. |
| Official Shape | Microsoft documents `GetVolumeInformationW` as returning file-system and volume information for a root directory, using the current directory root when `lpRootPathName` is NULL, and treating output fields as optional according to the supplied pointers and buffers. |
| Fix | Comment-only source clarification. The inactive registration and inactive body now name SREV-282, state that the hook remains dormant, and point future revival at a Windows proof and current caller contract. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-282.py` validates the draft-07 schema, official reference, inactive `file_init.c` registration, inactive `file_misc.c` body, active owner adjacency through SREV-273 and SREV-279, stale source wording removal, and ledger fragment; `docs/plan/check-srev-282.sh` is the targeted wrapper. Runtime gate: none for the current dormant hook state. Any future revival needs Windows proof covering the actual caller, all-null optional-output call shape, normal `GetVolumeInformationW` behavior, SREV-273 final-path adjacency, SREV-279 `NtQueryVolumeInformationFile` adjacency, and by-handle volume-info hook interaction. |
