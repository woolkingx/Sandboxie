# SREV-314: NSI Network Change Notification Shim

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/custom.c`, `Sandboxie/core/dll/ldr.c`, Microsoft network-change notification, NSI service, and RPC return documentation |
| Output artifact | private NSI notification shim contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `NsiRpc_NsiRpcRegisterChangeNotification` |
| Acceptance gate | Targeted checker validates official references, private-export boundary, `EPT_S_NOT_REGISTERED -> NO_ERROR` translation only, native result pass-through, loader table registration, combined ledger, and ledger fragment |

## Data

`ldr.c` registers `winnsi.dll` with `NsiRpc_Init`. When the DLL loads,
`NsiRpc_Init` resolves the private export `NsiRpcRegisterChangeNotification`
and hooks it. The hook calls the native export first, changes only
`EPT_S_NOT_REGISTERED` to `NO_ERROR`, and returns every other native result
unchanged.

Before this SREV, the source comment described the branch as a WinINet
workaround and mixed several possible routes. The behavior was already narrow,
but the owner boundary was not explicit: Sandboxie does not implement NSI
network-change notification topology here.

## Official Shape

Microsoft documents public network-change notification through APIs such as
`NotifyIpInterfaceChange`, which registers callbacks for changes to IP
interfaces and returns `NO_ERROR` on success.

Microsoft documents `CancelMibChangeNotify2` as the public cancellation owner
for change notifications registered by `NotifyIpInterfaceChange` and related
MIB notification APIs.

Microsoft service guidance documents the Network Store Interface service
(`nsi`) as delivering network notifications such as interface additions and
deletions to user-mode clients.

Microsoft RPC return documentation defines `EPT_S_NOT_REGISTERED` as no more
endpoints available from the endpoint-map database.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-notifyipinterfacechange`
- `https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-cancelmibchangenotify2`
- `https://learn.microsoft.com/en-us/windows-server/security/windows-services/security-guidelines-for-disabling-system-services-in-windows-server`
- `https://learn.microsoft.com/en-us/windows/win32/rpc/rpc-return-values`

## Schema

Local schema:

```text
docs/plan/srev-314-nsi-network-change-notification-shim.schema.json
```

Contract id:

```text
NSI_NETWORK_CHANGE_NOTIFICATION_SHIM
```

## Topology

```text
winnsi.dll load
  -> Ldr_Dlls entry
  -> NsiRpc_Init
  -> Ldr_GetProcAddrNew("NsiRpcRegisterChangeNotification")
  -> SBIEDLL_HOOK(NsiRpc_, NsiRpcRegisterChangeNotification)
  -> NsiRpc_NsiRpcRegisterChangeNotification
  -> native private export result
  -> EPT_S_NOT_REGISTERED becomes NO_ERROR
  -> every other result passes through unchanged
```

Boundary:

```text
WinINet / caller notification registration
  -> private winnsi export
  -> NSI service / endpoint mapper topology
```

Sandboxie owns only the narrow compatibility result mapping. It does not own a
replacement NSI notification subscription model in this hook.

## Logic Risk

The broad comment could make future changes look free to open wider RPC access
to the NSI service. The code does not prove that topology. The source behavior
is narrower and safer: try the native path, suppress only the endpoint-map miss
that breaks compatibility, and keep all other return values intact.

## Fix

`ldr.c` now names the `winnsi.dll` entry as the SREV-314 private NSI
network-change notification shim. `custom.c` now describes the exact result
mapping and the NSI boundary.

No hook registration condition, export name, native call, argument forwarding,
or return-value policy changed.

## Acceptance Gate

`docs/plan/check-srev-314.py` validates the draft-07 schema, official
references, loader table registration, private-export lookup, `SBIEDLL_HOOK`,
native call before mapping, `EPT_S_NOT_REGISTERED -> NO_ERROR` translation,
pass-through return, source comment boundary, combined ledger entry, and split
ledger fragment.

Runtime gate: Windows WinINet/NSI smoke proving certificate-revocation/network
initialization compatibility remains acceptable while no broader NSI RPC access
is granted by this hook.
