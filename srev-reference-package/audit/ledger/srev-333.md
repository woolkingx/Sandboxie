---
kind: srev-ledger-entry
id: SREV-333
title: File Filter Kaspersky Swmon Sentinel
status: patched-comment-topology-after-official-apc-wow64-ntsetinformationthread-review-no-behavior-change
owner: Sandboxie/core/drv/file_flt.c
spec: docs/plan/srev-333-file-flt-kaspersky-swmon-sentinel.md
schema: docs/plan/srev-333-file-flt-kaspersky-swmon-sentinel.schema.json
checker: docs/plan/check-srev-333.py
runtime_gate: Windows Kaspersky/WOW64 matrix for swmon sentinel and SREV-329 change-notify-token regression
---

### SREV-333: File Filter Kaspersky Swmon Sentinel

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official APC, WOW64, and `NtSetInformationThread` review; no behavior change |
| Evidence | `File_CheckFileObject` has an x64-only, pre-SbieDll-loaded predicate for file-object names matching component prefix `\swmon_` and suffix `_kl1`; matching names return `STATUS_BAD_INITIAL_PC`. The old comments called this a Kaspersky 2014 hack/workaround. The branch is tied to a comment about APC-patched WOW64 NTAPI stubs and the `Gui_ConnectToWindowStationAndDesktop` `NtSetInformationThread` path. |
| Data | `File_CheckFileObject`, `_WIN64`, `proc->sbiedll_loaded`, `NameString`, `wcsrchr`, `Backslash`, `Underscore`, `_wcsicmp(Underscore, L"_kl1")`, `_wcsnicmp(Backslash, L"\\swmon_", 7)`, `STATUS_BAD_INITIAL_PC`, `Syscall_OpenHandle`, WOW64, APC, `NtSetInformationThread`, `Gui_ConnectToWindowStationAndDesktop`, and SREV-329. |
| Schema | `FILE_FLT_KASPERSKY_SWMON_SENTINEL` says `File_CheckFileObject` owns only the early x64 pre-SbieDll-loaded `swmon_*_kl1` sentinel; the sentinel preserves later SbieDll `NtSetInformationThread` topology and does not own `NtSetInformationThread` semantics; `STATUS_BAD_INITIAL_PC` remains the local non-canceling sentinel consumed by `Syscall_OpenHandle`; the name predicate remains scoped to a component prefix `\swmon_` and suffix `_kl1`; SREV-329 owns the adjacent SbieDll `NtSetInformationThread` pass-through guard; this SREV changes comments and proof only. |
| Topology | `File_CheckFileObject -> _WIN64 -> !proc->sbiedll_loaded -> swmon_*_kl1 predicate -> STATUS_BAD_INITIAL_PC -> Syscall_OpenHandle non-canceling sentinel handling`. Adjacent SREV-329 topology remains `SbieDll NtSetInformationThread pass-through guard -> Gui_ConnectToWindowStationAndDesktop change-notify-token path`. |
| Logic Risk | Treating this as a broad third-party workaround could lead future edits to expand the name predicate, run it after SbieDll is loaded, or remove it without proving the `NtSetInformationThread` change-notify-token path under Kaspersky/WOW64 runtime conditions. |
| Official Shape | Microsoft documents `ZwSetInformationThread` / user-mode `NtSetInformationThread` as a thread-information operation with handle, class, buffer, length, and NTSTATUS result. Microsoft documents user APCs as queued to threads and warns against cross-process APCs because addresses and execution context can be wrong, including cross-architecture cases. Microsoft documents WOW64 as the x86 emulator that interposes between 32-bit NTDLL and the kernel and loads x86 NTDLL at startup. |
| Fix | Comment-only source clarification. The source now names SREV-333, the Kaspersky/WOW64/APC/`NtSetInformationThread` adjacency, and the narrow x64 pre-SbieDll-loaded `swmon_*_kl1` sentinel. No compile gate, load-stage gate, name predicate, return status, or `Syscall_OpenHandle` handling changed. |
| Acceptance Gate | `docs/plan/check-srev-333.py` validates the draft-07 schema, official references, source comment ownership, x64 and `!proc->sbiedll_loaded` gates, `swmon_` / `_kl1` matching, `STATUS_BAD_INITIAL_PC`, `Syscall_OpenHandle` sentinel handling, SREV-329 adjacency, stale hack/workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-333.sh` is the targeted wrapper. Runtime gate: Windows Kaspersky/WOW64 matrix covering pre-SbieDll load, post-SbieDll load, matching and non-matching `swmon_*_kl1` names, `Syscall_OpenHandle` non-canceling sentinel behavior, and SREV-329 `NtSetInformationThread` change-notify-token regression checks. |
