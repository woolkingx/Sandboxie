---
kind: srev-ledger-entry
id: SREV-083
title: GUI Device Notification Fake Handle Boundary
status: patched-source-level-after-official-registerdevicenotification-unregisterdevicen
owner: Sandboxie/core/dll/gui.c
spec: docs/plan/srev-083-gui-device-notification-fake-handle.md
schema: docs/plan/srev-083-gui-device-notification-fake-handle.schema.json
checker: docs/plan/check-srev-083.py
runtime_gate: "with `BlockRegisterDeviceNotification=y`, fake registrations can be unregistered successfully; a real or invalid non-fake `HDEVNOTIFY` is not silently accepted by the Sandboxie hook and follows user32 behavior"
---
### SREV-083: GUI Device Notification Fake Handle Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `RegisterDeviceNotification` / `UnregisterDeviceNotification` handle-owner shape; needs Windows device-notification runtime proof |
| Evidence | `Sandboxie/core/dll/gui.c` conditionally hooks `RegisterDeviceNotificationA/W` and `UnregisterDeviceNotification` when `BlockRegisterDeviceNotification` is enabled. Microsoft documents `RegisterDeviceNotificationA/W` as returning a device notification handle on success and documents that returned handles must be closed with `UnregisterDeviceNotification`. Microsoft documents `UnregisterDeviceNotification` as closing the specified device notification handle, returning nonzero on success and zero on failure. Before this patch, the block hook returned hardcoded `0x12345678` for all fake registrations, and `Gui_UnregisterDeviceNotification` returned success for every input handle. |
| Data | Register request, recipient/filter/flags, fake device-notification handle, unregister input handle, real user32 unregister fallback, and `GetLastError` projection. |
| Schema | `GUI_DEVICE_NOTIFICATION_FAKE_HANDLE` says blocked registration returns a non-NULL fake handle owned by `gui.c`; the fake handle is a process-local cookie rather than a magic integer; unregister succeeds locally only for that fake handle; non-fake unregister handles are forwarded to the real user32 owner; the hook does not convert arbitrary handles into successful unregisters. |
| Topology | Caller `RegisterDeviceNotificationA/W` crosses into the block hook and receives a process-local fake cookie. Caller `UnregisterDeviceNotification` crosses into the hook; the fake cookie is consumed locally, while all other handles remain owned by user32 and are forwarded to `__sys_UnregisterDeviceNotification`. |
| Logic Risk | A compatibility stub that suppresses device notifications should not also become an arbitrary-success close operation. Returning success for every unregister input can hide invalid-handle bugs and can prevent real notification handles from being closed by their actual owner. A fixed magic integer also has no owner identity beyond convention. |
| Official Shape | `docs/plan/srev-083-gui-device-notification-fake-handle.md` records Microsoft `RegisterDeviceNotificationA`, `RegisterDeviceNotificationW`, and `UnregisterDeviceNotification` references. `docs/plan/srev-083-gui-device-notification-fake-handle.schema.json` records the JSON Schema draft-07 local `GUI_DEVICE_NOTIFICATION_FAKE_HANDLE` contract. |
| Fix | `Gui_RegisterDeviceNotificationA/W` now returns a process-local static cookie address as the fake handle. `Gui_UnregisterDeviceNotification` returns local success only for that fake cookie and forwards every non-fake handle to `__sys_UnregisterDeviceNotification`. |
| Acceptance Gate | `docs/plan/check-srev-083.py` validates the draft-07 schema, official references, fake cookie declaration, A/W fake-handle returns, stale magic constant removal, non-fake forwarding to the real API, and ledger entry; `docs/plan/check-srev-083.sh` is the matrix wrapper. Windows gate: with `BlockRegisterDeviceNotification=y`, fake registrations can be unregistered successfully; a real or invalid non-fake `HDEVNOTIFY` is not silently accepted by the Sandboxie hook and follows user32 behavior. |
