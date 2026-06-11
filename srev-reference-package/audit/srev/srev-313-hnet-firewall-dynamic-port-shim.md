# SREV-313: HNet Firewall Dynamic Port Shim

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/netapi.c`, `Sandboxie/core/dll/ldr.c`, Microsoft Windows Firewall and HRESULT documentation |
| Output artifact | hnetcfg dynamic-port compatibility contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `HNet_IcfOpenDynamicFwPort` |
| Acceptance gate | Targeted checker validates official references, private-export boundary, `S_OK` HRESULT success shape, no call into host firewall mutation, loader table registration, combined ledger, and ledger fragment |

## Data

`ldr.c` registers `hnetcfg.dll` with `HNet_Init`. When that DLL loads,
`HNet_Init` resolves the private export `IcfOpenDynamicFwPort` and hooks it
when present. The hook does not call the native export; it returns success to
the caller.

Before this SREV, the source described the branch only as a firewall workaround
and returned literal `0`. The behavior was already non-mutating, but the source
did not name the owner boundary: a sandboxed application does not own host
Windows Firewall policy changes.

## Official Shape

Microsoft documents Windows Firewall open-port policy through COM interfaces
such as `INetFwOpenPort`, where an open port has protocol, port, name, scope,
remote-address, enabled, and built-in status properties.

Microsoft documents Windows Firewall policy through `INetFwPolicy2`, the
firewall settings object that controls profiles, rules, and service
restrictions.

Microsoft documents HRESULT/COM success through `S_OK`.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/netfw/nn-netfw-inetfwopenport`
- `https://learn.microsoft.com/en-us/windows/win32/api/netfw/nn-netfw-inetfwpolicy2`
- `https://learn.microsoft.com/en-us/windows/win32/seccrypto/common-hresult-values`

## Schema

Local schema:

```text
docs/plan/srev-313-hnet-firewall-dynamic-port-shim.schema.json
```

Contract id:

```text
HNET_FIREWALL_DYNAMIC_PORT_SHIM
```

## Topology

```text
hnetcfg.dll load
  -> Ldr_Dlls entry
  -> HNet_Init
  -> GetProcAddress("IcfOpenDynamicFwPort")
  -> SBIEDLL_HOOK(HNet_, IcfOpenDynamicFwPort)
  -> HNet_IcfOpenDynamicFwPort
  -> S_OK without host firewall mutation
```

Boundary:

```text
sandboxed Winsock bind compatibility
  -> private hnetcfg export
  -> host Windows Firewall policy owner
```

Sandboxie owns only the compatibility shim. It does not own adding firewall
exceptions or changing host firewall policy from the sandboxed process.

## Logic Risk

The old comment made the branch sound like a generic firewall workaround. That
can misroute future patches toward opening host firewall policy from inside a
sandboxed process. The safer schema is narrower: the hook is a private-export
compatibility shim that reports success to preserve local bind behavior while
deliberately not mutating host firewall policy.

## Fix

`ldr.c` now names the `hnetcfg.dll` entry as the SREV-313 private hnetcfg
firewall dynamic-port shim. `HNet_IcfOpenDynamicFwPort` now documents the host
firewall policy boundary and returns `S_OK` instead of literal `0`.

No hook registration condition, export name, native-call suppression, or caller
argument handling changed.

## Acceptance Gate

`docs/plan/check-srev-313.py` validates the draft-07 schema, official
references, loader table registration, `GetProcAddress` private-export lookup,
`SBIEDLL_HOOK`, `S_OK` return, absence of a native
`__sys_IcfOpenDynamicFwPort` call from the hook body, source comment boundary,
combined ledger entry, and split ledger fragment.

Runtime gate: Windows bind/firewall smoke proving sandboxed bind compatibility
is preserved while no host Windows Firewall rule/open-port policy is added.
