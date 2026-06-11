# SREV-289: GUI Device Notification Init Gate Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/gui.c`, SREV-083, Microsoft RegisterDeviceNotification/UnregisterDeviceNotification references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_Init` configuration gate for `Gui_Init3` device-notification hooks |
| Acceptance gate | Targeted checker validates official references, config gate, `Gui_Init3` hook group, SREV-083 adjacency, stale todo removal, and ledger fragment |

## Data

`Gui_Init` initializes GUI submodules in sequence and calls `Gui_Init3` only
when:

```text
ok == TRUE
BlockRegisterDeviceNotification == TRUE
```

`Gui_Init3` installs the `RegisterDeviceNotificationA/W` and
`UnregisterDeviceNotification` hooks. SREV-083 owns the fake notification handle
and unregister-forwarding behavior behind those hooks.

## Official Shape

Microsoft documents `RegisterDeviceNotificationA/W` as returning a device
notification handle on success and documents that returned handles must be
closed with `UnregisterDeviceNotification`.

Microsoft documents `UnregisterDeviceNotification` as closing a device
notification handle; success returns nonzero and failure returns zero.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerdevicenotificationa`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerdevicenotificationw`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-unregisterdevicenotification`

## Schema

Local schema:

```text
docs/plan/srev-289-gui-device-notification-init-gate-owner.schema.json
```

Contract id:

```text
GUI_DEVICE_NOTIFICATION_INIT_GATE_OWNER
```

## Boundary

```text
Gui_Init submodule sequence
  -> BlockRegisterDeviceNotification config gate
  -> Gui_Init3 hook group
  -> SREV-083 fake notification-handle contract
```

The init gate owns only whether the hook group is installed. SREV-083 owns the
runtime fake-handle and unregister behavior after installation.

## Topology

```text
user32.dll load
  -> Gui_Init
  -> GUI import resolution
  -> GUI submodule init chain
  -> BlockRegisterDeviceNotification
  -> Gui_Init3
    -> RegisterDeviceNotificationA/W hook selection
    -> UnregisterDeviceNotification hook
```

`Gui_Init3` handles the local A/W export-alias shape by installing only the W
hook when A and W resolve to the same address, otherwise installing both hooks.

## Logic Risk

The old inline `todo remove later` comment made the hook group look like
temporary residue. That can misroute future cleanup into removing the optional
configuration gate without re-proving SREV-083's runtime contract. The legal
owner is the setting-gated device-notification block hook group.

## Fix

Comment-only source clarification. The call site now names SREV-289 and the
optional SREV-083 notification-block hook group. No configuration key, submodule
ordering, hook selection, hook installation, or fake-handle behavior changed.

## Acceptance Gate

`docs/plan/check-srev-289.py` validates the draft-07 schema, official
references, `Gui_Init` config gate, `Gui_Init3` A/W alias hook topology,
SREV-083 adjacency, unchanged hook behavior, stale todo removal, combined
ledger entry, and split ledger fragment.

Runtime gate is inherited from SREV-083: Windows device-notification behavior
with `BlockRegisterDeviceNotification=y`, fake-registration unregister success,
and non-fake handle forwarding to user32.
