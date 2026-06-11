# SREV-049: COM ClosedRT Multi-String Drift

## Data

`Sandboxie/core/dll/com.c` `Com_LoadRTList` reads `ClosedRT` configuration
entries into a cached `WCHAR` multi-string. `Com_IsClosedRT` later walks that
multi-string to decide whether `Com_RoGetActivationFactory` should deny a
Windows Runtime activation.

The comments around `Com_IsClosedRT` admit two compatibility blocks:

- Chrome can crash when `Windows.System.Launcher` activation returns a shape it
  does not handle.
- `Windows.UI.Notifications.ToastNotificationManager` can deadlock with boxed
  COM.

## Official Shape

Microsoft documents `RoGetActivationFactory` as receiving an `HSTRING`
`activatableClassId`, a `REFIID`, and an output activation factory pointer:

```text
https://learn.microsoft.com/en-us/windows/win32/api/roapi/nf-roapi-rogetactivationfactory
```

Microsoft documents `HSTRING` as a Windows Runtime immutable string handle and
names `WindowsGetStringRawBuffer` as the API for accessing its backing string:

```text
https://learn.microsoft.com/en-us/windows/win32/winrt/hstring
```

## Schema

Local schema:

```text
docs/plan/srev-049-com-closedrt-list.schema.json
```

The cached `ClosedRT` list is a NUL-separated WCHAR list with an empty final
string. A second-pass configuration drift must produce a shorter valid list, not
uninitialized data or a write past the originally counted capacity.

## Topology

```text
configuration setting -> Com_LoadRTList -> cached ClosedRT multi-string
cached ClosedRT multi-string -> Com_IsClosedRT -> Com_RoGetActivationFactory
```

The COM activation hook owns the compatibility decision. Configuration is input
data; it does not own the memory layout of the cached list.

## Logic Risk

Before this patch, `Com_LoadRTList` counted entries in one pass, allocated the
exact multi-string capacity, and then read the configuration again to copy
entries. The allocated buffer is not zero-initialized by `Com_Alloc`.

If the second pass returns fewer entries than the first pass, the first WCHAR can
remain uninitialized and `Com_IsClosedRT` can walk garbage. If the second pass
returns a longer entry set than the first pass, `wcscpy` can write past the
capacity counted by the first pass.

## Fix

`Com_LoadRTList` now initializes the first WCHAR to NUL before the copy pass and
checks each copied entry against the remaining capacity while preserving space
for the final empty string. If the second pass drifts, it leaves a shorter valid
multi-string.

## Acceptance Gate

`docs/plan/check-srev-049.py` validates the draft-07 schema, official reference
links, the initialized sentinel before the second pass, the per-entry remaining
capacity gate, and the final terminator at `cur_pos`.

Windows gate: exercise `ClosedRT` with no entries, one entry, image-filtered
entries, and runtime config reload/drift while repeatedly calling
`RoGetActivationFactory` for allowed and denied runtime classes.
