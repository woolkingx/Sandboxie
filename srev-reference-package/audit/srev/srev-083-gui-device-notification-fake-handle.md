# SREV-083: GUI Device Notification Fake Handle Boundary

## Data

`Sandboxie/core/dll/gui.c` optionally hooks `RegisterDeviceNotificationA`,
`RegisterDeviceNotificationW`, and `UnregisterDeviceNotification` when the
`BlockRegisterDeviceNotification` setting is enabled.

The relevant data nodes are:

```text
RegisterDeviceNotificationA/W request
notification recipient and filter
fake device notification handle
UnregisterDeviceNotification input handle
real user32 unregister fallback
GetLastError projection
```

## Official Shape

Microsoft documents `RegisterDeviceNotificationA/W` as returning a device
notification handle on success and NULL on failure. Device notification handles
returned by `RegisterDeviceNotification` must be closed by
`UnregisterDeviceNotification` when they are no longer needed.

Microsoft documents `UnregisterDeviceNotification` as closing the specified
device notification handle; success returns nonzero, failure returns zero and
extended error information is available through `GetLastError`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerdevicenotificationa
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerdevicenotificationw
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-unregisterdevicenotification
```

## Schema

Local schema:

```text
docs/plan/srev-083-gui-device-notification-fake-handle.schema.json
```

The fake-handle contract is:

```text
blocked RegisterDeviceNotification returns a non-NULL fake handle owned by gui.c
the fake handle is a process-local cookie, not a magic integer
UnregisterDeviceNotification succeeds locally only for the fake handle
non-fake unregister handles are forwarded to the real user32 owner
the hook does not convert arbitrary handles into successful unregisters
```

## Topology

```text
caller RegisterDeviceNotificationA/W
  -> Gui_RegisterDeviceNotificationA/W
  -> process-local fake cookie
caller UnregisterDeviceNotification
  -> fake-cookie close locally OR real user32 unregister
```

`gui.c` owns only the fake registration it creates. The real user32 API remains
the owner for all non-fake notification handles.

## Logic Risk

Before this patch, the block hook returned a hardcoded integer
`0x12345678` as a fake notification handle, and
`Gui_UnregisterDeviceNotification` returned success for every input handle.
That widened a compatibility stub into an arbitrary-success unregister path and
could hide invalid-handle bugs or prevent real notification handles from being
closed by user32.

## Fix

`Gui_RegisterDeviceNotificationA/W` now returns the address of a static
process-local cookie as its fake handle. `Gui_UnregisterDeviceNotification`
returns local success only for that fake cookie and forwards every other handle
to `__sys_UnregisterDeviceNotification`.

## Acceptance Gate

`docs/plan/check-srev-083.py` validates the draft-07 schema, official
references, fake cookie declaration, A/W fake-handle returns, removal of the
magic constant, non-fake forwarding to the real API, and ledger entry.

Windows gate: with `BlockRegisterDeviceNotification=y`, fake registrations can
be unregistered successfully; a real or invalid non-fake `HDEVNOTIFY` is not
silently accepted by the Sandboxie hook and follows user32 behavior.
