---
kind: srev-ledger-entry
id: SREV-254
title: COM Built-In WinRT Denylist Boundary
status: patched-comment-topology-after-official-rogetactivationfactory-and-winrt-class-review-no-behavior-change
owner: Sandboxie/core/dll/com.c
spec: docs/plan/srev-254-com-built-in-winrt-denylist-boundary.md
schema: docs/plan/srev-254-com-built-in-winrt-denylist-boundary.schema.json
checker: docs/plan/check-srev-254.py
runtime_gate: Inherited from SREV-049 boxed COM open COM DisableRTBlacklist ClosedRT Chrome Launcher ToastNotificationManager and allowed WinRT activation need Windows runtime proof
---

### SREV-254: COM Built-In WinRT Denylist Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official RoGetActivationFactory and WinRT class review; no behavior change |
| Evidence | SREV-049 fixed the `ClosedRT` cached multi-string memory shape, but the same source area still carried informal compatibility comments for the built-in runtime-class deny-list. `Windows.System.Launcher` is denied for Chrome when boxed COM owns activation. `Windows.UI.Notifications.ToastNotificationManager` is denied when boxed COM owns activation. Those comments described symptoms rather than the owner boundary. |
| Data | `HSTRING activatableClassId`, `WindowsGetStringRawBuffer`, `Com_IsClosedRT`, `Com_RoGetActivationFactory`, `Ipc_OpenCOM`, `Dll_CompartmentMode`, `DisableRTBlacklist`, `ClosedRT`, `Windows.System.Launcher`, `Windows.UI.Notifications.ToastNotificationManager`, and `E_ACCESSDENIED`. |
| Schema | `COM_BUILT_IN_WINRT_DENYLIST_BOUNDARY` says `Com_RoGetActivationFactory` owns the local activation-factory hook and uses `WindowsGetStringRawBuffer` as the HSTRING inspection boundary; `Com_IsClosedRT` owns the built-in runtime-class deny-list before native activation; the built-in deny-list applies only when boxed COM owns activation and `DisableRTBlacklist` is not enabled; open COM plus compartment mode routes activation to the original COM/WinRT owner instead of this built-in deny-list; source comments must describe owner and topology, not only historical application symptoms; this SREV does not change denied runtime classes, monitor logging, `ClosedRT` configuration, HSTRING handling, or native activation forwarding. |
| Topology | `RoGetActivationFactory input HSTRING -> WindowsGetStringRawBuffer -> Com_IsClosedRT built-in deny-list and ClosedRT config list -> deny with E_ACCESSDENIED or forward to native RoGetActivationFactory`. |
| Logic Risk | Symptom-only comments can misroute future work toward opening COM, switching to the original token, or adding application-specific bypasses. The correct local shape is a deny-list boundary in front of native WinRT activation, with open COM remaining the separate owner for cases that require the original activation environment. |
| Official Shape | `docs/plan/srev-254-com-built-in-winrt-denylist-boundary.md` records Microsoft `RoGetActivationFactory`, `HSTRING`, `Windows.System.Launcher`, and `Windows.UI.Notifications.ToastNotificationManager` references. `docs/plan/srev-254-com-built-in-winrt-denylist-boundary.schema.json` records the JSON Schema draft-07 local `COM_BUILT_IN_WINRT_DENYLIST_BOUNDARY` contract. |
| Fix | Comment-only source clarification. The `Windows.System.Launcher` and `Windows.UI.Notifications.ToastNotificationManager` comments now describe the boxed COM boundary and built-in ClosedRT deny-list owner. No runtime-class ID, predicate, return value, monitor event, config setting, or native forwarding path changed. |
| Acceptance Gate | `docs/plan/check-srev-254.py` validates the draft-07 schema, official reference links, the source-level built-in deny-list predicates, the clarified source comments, removal of symptom-only terms from the `Com_IsClosedRT` comment block, SREV-049 adjacency, and the ledger fragment; `docs/plan/check-srev-254.sh` is the targeted wrapper. Runtime gate is inherited from SREV-049: Windows proof still needs allowed and denied WinRT activation smoke for boxed COM, open COM plus compartment mode, `DisableRTBlacklist`, `ClosedRT`, Chrome `Windows.System.Launcher`, and `Windows.UI.Notifications.ToastNotificationManager`. |
