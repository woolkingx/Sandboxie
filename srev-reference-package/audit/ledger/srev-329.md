---
kind: srev-ledger-entry
id: SREV-329
title: SXS NtSetInformationThread Pass-Through Hook
status: source-comment-classified-after-official-ntsetinformationthread-shape-review-no-behavior-change
owner: Sandboxie/core/dll/sxs.c
spec: docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.md
schema: docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.schema.json
checker: docs/plan/check-srev-329.py
runtime_gate: Browser/runtime matrix covering Opera-like patched NTAPI stubs and modern Chromium/Firefox/Thunderbird scenarios should prove whether removing the SXS NtSetInformationThread pass-through hook preserves the change-notify-token path and does not regress normal thread-information calls
---
### SREV-329: SXS NtSetInformationThread Pass-Through Hook

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | source comment classified after official `NtSetInformationThread` / `ZwSetInformationThread` shape review; no source behavior change |
| Evidence | `Sandboxie/core/dll/sxs.c` installs `SBIEDLL_HOOK(Sxs_, NtSetInformationThread)` from `Sxs_InitKernel32`. The wrapper `Sxs_NtSetInformationThread` forwards `ThreadHandle`, `ThreadInformationClass`, `ThreadInformation`, and `ThreadInformationLength` unchanged to `__sys_NtSetInformationThread` and returns the native NTSTATUS. The old comment said an Opera-specific reason seemed no longer required, but the hook remains active. `Sandboxie/core/dll/gui.c` references `Thread_SetInformationThread_ChangeNotifyToken` and prefers `__sys_NtSetInformationThread` when available; `Sandboxie/core/drv/thread_token.c` owns the driver-side special info-class path. |
| Data | `Sxs_InitKernel32`, `GetProcAddress(Dll_Ntdll, "NtSetInformationThread")`, `SBIEDLL_HOOK(Sxs_, NtSetInformationThread)`, `Sxs_NtSetInformationThread`, `__sys_NtSetInformationThread`, `ThreadHandle`, `ThreadInformationClass`, `ThreadInformation`, `ThreadInformationLength`, `Gui_ConnectToWindowStationAndDesktop`, and `Thread_SetInformationThread_ChangeNotifyToken`. |
| Schema | `SXS_NTSETINFORMATIONTHREAD_PASS_THROUGH_HOOK` says `NtSetInformationThread` owns the thread-information transition and NTSTATUS result; `Sxs_NtSetInformationThread` must preserve arguments and return the native NTSTATUS; the SXS hook changes call topology even when it preserves native semantics; GUI/driver comments provide adjacent change-notify-token evidence; removing the hook requires Windows browser/runtime proof; this SREV changes comments and proof only. |
| Topology | `Sxs_InitKernel32 -> GetProcAddress(Dll_Ntdll, "NtSetInformationThread") -> SBIEDLL_HOOK(Sxs_, NtSetInformationThread) -> Sxs_NtSetInformationThread -> __sys_NtSetInformationThread(arguments unchanged) -> native NTSTATUS result`. |
| Logic Risk | The old comment mixed an Opera-specific historical reason with a claim that the path may no longer be required. Because the hook remains active, that comment can misroute future work into deleting it as stale cleanup. The local contract is narrower: the hook is a pass-through topology guard and must preserve the native `NtSetInformationThread` argument/result shape until a Windows runtime matrix proves it can be removed. |
| Official Shape | `docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.md` records Microsoft `ZwSetInformationThread` / user-mode `NtSetInformationThread` reference. `docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.schema.json` records the JSON Schema draft-07 local `SXS_NTSETINFORMATIONTHREAD_PASS_THROUGH_HOOK` contract. |
| Fix | Comment-only source clarification. The source now names SREV-329 and states that the hook is a narrow `NtSetInformationThread` pass-through guard for the change-notify-token path referenced by `Gui_ConnectToWindowStationAndDesktop`. It also records that removal needs Windows browser matrix proof because the hook still changes call topology. No `GetProcAddress`, `SBIEDLL_HOOK`, wrapper function signature, argument forwarding, native `__sys_NtSetInformationThread` call, return value, or adjacent GUI/driver change-notify-token behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-329.py` validates the draft-07 schema, official reference, pass-through wrapper, hook installation, adjacent GUI/driver change-notify-token evidence, stale Opera/workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-329.sh` is the targeted wrapper. Windows gate: browser/runtime matrix covering Opera-like patched NTAPI stubs and modern Chromium/Firefox/Thunderbird scenarios should prove whether removing the SXS `NtSetInformationThread` pass-through hook preserves the change-notify-token path and does not regress normal thread-information calls. |
