# SREV-254: COM Built-In WinRT Denylist Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/com.c`, SREV-049, Microsoft `RoGetActivationFactory`, `HSTRING`, `Windows.System.Launcher`, and `Windows.UI.Notifications.ToastNotificationManager` references |
| Output artifact | `docs/plan/srev-254-com-built-in-winrt-denylist-boundary.schema.json`, `docs/plan/check-srev-254.py`, `docs/plan/check-srev-254.sh`, ledger fragment, comment-only source clarification |
| Owner | `Com_IsClosedRT` built-in Windows Runtime activation deny-list |
| Acceptance gate | targeted source checker, SREV-049 compatibility checker, core coverage, and diff checkpoint |

## Evidence

SREV-049 fixed the `Com_LoadRTList` cached `ClosedRT` multi-string memory
shape, but the same source area still carried informal compatibility comments
for the built-in runtime-class deny-list:

- `Windows.System.Launcher` is denied for Chrome when boxed COM owns activation.
- `Windows.UI.Notifications.ToastNotificationManager` is denied when boxed COM
  owns activation.

Those comments described symptoms rather than the owner boundary. The local
owner is `Com_IsClosedRT`: it decides whether `Com_RoGetActivationFactory`
should deny a runtime-class activation before calling the native
`RoGetActivationFactory`.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/roapi/nf-roapi-rogetactivationfactory
- https://learn.microsoft.com/en-us/windows/win32/winrt/hstring
- https://learn.microsoft.com/en-us/uwp/api/windows.system.launcher
- https://learn.microsoft.com/en-us/uwp/api/windows.ui.notifications.toastnotificationmanager

## Data

`HSTRING activatableClassId`, `WindowsGetStringRawBuffer`,
`Com_IsClosedRT`, `Com_RoGetActivationFactory`, `Ipc_OpenCOM`,
`Dll_CompartmentMode`, `DisableRTBlacklist`, `ClosedRT`,
`Windows.System.Launcher`, `Windows.UI.Notifications.ToastNotificationManager`,
and `E_ACCESSDENIED`.

## Schema

`COM_BUILT_IN_WINRT_DENYLIST_BOUNDARY` says:

- `Com_RoGetActivationFactory` owns the local activation-factory hook and uses
  `WindowsGetStringRawBuffer` as the HSTRING inspection boundary;
- `Com_IsClosedRT` owns the built-in runtime-class deny-list before native
  activation;
- the built-in deny-list applies only when boxed COM owns activation and
  `DisableRTBlacklist` is not enabled;
- open COM plus compartment mode routes activation to the original COM/WinRT
  owner instead of this built-in deny-list;
- source comments must describe owner and topology, not only historical
  application symptoms;
- this SREV does not change denied runtime classes, monitor logging,
  `ClosedRT` configuration, HSTRING handling, or native activation forwarding.

## Topology

```text
RoGetActivationFactory input HSTRING
  -> WindowsGetStringRawBuffer
  -> Com_IsClosedRT built-in deny-list and ClosedRT config list
  -> deny with E_ACCESSDENIED or forward to native RoGetActivationFactory
```

The built-in entries are compatibility policy at the activation boundary. They
are not a reason to switch tokens, broaden COM access, or reinterpret the
`ClosedRT` configuration cache fixed by SREV-049.

## Logic Risk

Symptom-only comments can misroute future work toward opening COM, switching to
the original token, or adding application-specific bypasses. The correct local
shape is a deny-list boundary in front of native WinRT activation, with open COM
remaining the separate owner for cases that require the original activation
environment.

## Fix

Comment-only source clarification. The `Windows.System.Launcher` and
`Windows.UI.Notifications.ToastNotificationManager` comments now describe the
boxed COM boundary and built-in ClosedRT deny-list owner. No runtime-class ID,
predicate, return value, monitor event, config setting, or native forwarding path
changed.

## Acceptance Gate

`docs/plan/check-srev-254.py` validates the draft-07 schema, official reference
links, the source-level built-in deny-list predicates, the clarified source
comments, removal of symptom-only terms from the `Com_IsClosedRT` comment block,
SREV-049 adjacency, and the ledger fragment.

Runtime gate: inherited from SREV-049. Windows proof still needs allowed and
denied WinRT activation smoke for boxed COM, open COM plus compartment mode,
`DisableRTBlacklist`, `ClosedRT`, Chrome `Windows.System.Launcher`, and
`Windows.UI.Notifications.ToastNotificationManager`.
