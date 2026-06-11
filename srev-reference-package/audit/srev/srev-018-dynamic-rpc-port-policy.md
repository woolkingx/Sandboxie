# SREV-018 Dynamic RPC Port Policy Entry Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents dynamic RPC endpoints as endpoint-map entries associated
with a server interface UUID/version, binding handle, and optional object UUID.
`RpcEpRegister` adds or replaces server address information in the local
endpoint-map database. For an existing matching entry, it replaces the endpoint
with the endpoint in the provided binding handle.

The Win32 RPC endpoint guidance says the endpoint mapper resolves partially
bound client handles by matching interface UUID, major version, protocol
sequence, optional object UUID, and compatible minor version; if matched, the
endpoint mapper returns the valid endpoint. Dynamic endpoints are removed when
the server process stops or when explicitly unregistered.

MS-RPCE describes dynamic endpoint registration as registering the list of
endpoints associated with the interface UUID/version and object UUID with the
local endpoint mapper. Its tower-encoding interpretation requires local
registration and treats tower structure as the endpoint-map carrier.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcepregister
- https://learn.microsoft.com/en-us/windows/win32/rpc/specifying-endpoints
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rpce/ff7e452a-8d7e-447f-affc-67dc43cf7a61
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rpce/68123428-ebee-4a30-842e-6c9212afe931

## Local Shape

Sandboxie projects selected endpoint-map results into driver-owned
`IPC_DYNAMIC_PORT` entries:

- `wstrPortId`: local policy identity such as `spooler`
- `wstrPortName`: current dynamic `\RPC Control\...` endpoint name
- `FilterCount` / `FilterIDs[]`: message-id deny policy for that endpoint

`Ipc_CheckPortRequest_Dynamic` later enforces the entry by matching the current
port name and applying `FilterIDs[]` to the parsed RPC message id.

## Local Risk

The previous registration path treated a repeated `wstrPortId` as an in-place
name refresh only. It copied the new endpoint name but kept the old
`FilterCount` and `FilterIDs[]`.

That makes the policy entry internally inconsistent when configuration or
endpoint classification changes: the endpoint-map projection points at the
new dynamic port name while enforcing the stale filter list from an earlier
registration.

## Patch Boundary

Treat `IPC_DYNAMIC_PORT` as an immutable policy entry after publication.
Re-registration with the same `wstrPortId` constructs a full replacement entry
from the new endpoint name and filter list, verifies the filter payload before
taking the global port lock, then atomically swaps the list node under the
existing exclusive lock.

Preserve current behavior otherwise:

- only SbieSvc can call `API_OPEN_DYNAMIC_PORT`
- sandboxed callers still cannot call the driver API directly
- process-specific `Process_AddPath` behavior is unchanged
- `spooler` cache pointer follows the replaced entry

## Acceptance Gate

- Re-registration replaces both `wstrPortName` and `FilterIDs[]`.
- The old flexible-array entry is freed with its original allocation size.
- The new entry is only published after the filter payload is probed/copied.
- Runtime gate remains open: register id with filter A, re-register same id
  with filter B, then verify only filter B is enforced for the current port.
