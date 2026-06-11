---
kind: srev-ledger-entry
id: SREV-289
title: GUI Device Notification Init Gate Owner
status: patched-comment-topology-after-srev-083-device-notification-review-no-behavior-change
owner: Sandboxie/core/dll/gui.c
spec: docs/plan/srev-289-gui-device-notification-init-gate-owner.md
schema: docs/plan/srev-289-gui-device-notification-init-gate-owner.schema.json
checker: docs/plan/check-srev-289.py
runtime_gate: inherited from SREV-083 Windows BlockRegisterDeviceNotification fake registration unregister success and non-fake handle forwarding
---

### SREV-289: GUI Device Notification Init Gate Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-083 device-notification review; no behavior change |
| Evidence | `Gui_Init` calls `Gui_Init3(module)` only when prior GUI submodule initialization is still successful and `BlockRegisterDeviceNotification` is enabled. `Gui_Init3` installs `RegisterDeviceNotificationA/W` and `UnregisterDeviceNotification` hooks, preserving the existing same-address A/W alias branch. SREV-083 already owns the fake notification-handle and unregister-forwarding behavior behind those hooks. The remaining call-site comment said `todo remove later`, which hid the current configuration-gated owner boundary. |
| Data | `Gui_Init`, `ok`, `SbieApi_QueryConfBool`, `BlockRegisterDeviceNotification`, `Gui_Init3`, `RegisterDeviceNotificationA`, `RegisterDeviceNotificationW`, `UnregisterDeviceNotification`, A/W same-address branch, and SREV-083 fake notification handle contract. |
| Schema | `GUI_DEVICE_NOTIFICATION_INIT_GATE_OWNER` says `Gui_Init` owns only the `BlockRegisterDeviceNotification` configuration gate for `Gui_Init3`; `Gui_Init3` owns the `RegisterDeviceNotificationA/W` and `UnregisterDeviceNotification` hook group installation; SREV-083 owns the fake notification handle and unregister forwarding runtime behavior; A and W hooks preserve the existing same-address alias branch; this SREV changes comments and proof only. |
| Topology | `user32.dll load -> Gui_Init -> GUI import resolution -> GUI submodule init chain -> BlockRegisterDeviceNotification -> Gui_Init3 -> RegisterDeviceNotificationA/W hook selection -> UnregisterDeviceNotification hook -> SREV-083 fake notification-handle contract`. |
| Logic Risk | The temporary-looking todo can make a valid setting-gated hook group look disposable. Removing it without re-proving SREV-083 would silently drop the configured device-notification block behavior. |
| Official Shape | Microsoft documents `RegisterDeviceNotificationA/W` as returning device-notification handles that must be closed by `UnregisterDeviceNotification`; `UnregisterDeviceNotification` closes such handles and reports success or failure. |
| Fix | Comment-only source clarification. The call site now names SREV-289 and the optional SREV-083 notification-block hook group. No configuration key, submodule ordering, hook selection, hook installation, or fake-handle behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-289.py` validates the draft-07 schema, official references, `Gui_Init` config gate, `Gui_Init3` A/W alias hook topology, SREV-083 adjacency, unchanged hook behavior, stale todo removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-289.sh` is the targeted wrapper. Runtime gate is inherited from SREV-083: Windows device-notification behavior with `BlockRegisterDeviceNotification=y`, fake-registration unregister success, and non-fake handle forwarding to user32. |
