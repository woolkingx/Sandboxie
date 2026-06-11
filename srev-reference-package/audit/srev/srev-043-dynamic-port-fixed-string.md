# SREV-043: Dynamic Port Fixed String

## Finding

`Sandboxie/core/drv/ipc_port.c` `Ipc_Api_OpenDynamicPort` accepts a required
dynamic RPC port name and optional dynamic port identifier as user `WCHAR*`
pointers. The handler probed the full fixed buffer size and then copied
`DYNAMIC_PORT_*_CHARS - 1` WCHARs before appending a local NUL terminator. If
the user input was overlong and not terminated before the local cap, the driver
silently truncated the port name or identifier before inserting or matching
dynamic IPC topology.

## Official Shape

- `ProbeForRead` validates user buffer access using a byte length and required
  alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-043-dynamic-port-fixed-string.schema.json
```

`port_name` is required. `port_id` is optional and only used for special dynamic
port registration. Present fixed strings must be readable under the existing
local caps, WCHAR-aligned, non-empty, and NUL-terminated before the final local
terminator slot. Overlong unterminated input is invalid, not a candidate for
truncation.

## Fix

`Ipc_Api_OpenDynamicPort` now copies `port_name` and present `port_id` through
`Ipc_CopyFixedUserWString`, which rejects NULL, empty, and overlong unterminated
input before the local buffers enter `Ipc_CreateDynamicPort`,
`Process_AddPath`, or dynamic-port matching.

## Acceptance Gate

`docs/plan/check-srev-043.py` validates the local schema, official reference,
source helper shape, removal of fixed-length truncating `wmemcpy`, and that both
`port_name` and `port_id` route through the helper.

Windows gate still needed: dynamic port open/register with valid port name,
valid special port id, empty name/id, and overlong unterminated name/id.
