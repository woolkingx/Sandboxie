# SREV-324: RPCRT Disabled UserMgrCli COM Policy Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/rpcrt.c`, `Sandboxie/core/dll/com.c`, `Sandboxie/install/Templates.ini`, Microsoft RPC and COM references |
| Output artifact | `docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.schema.json`, `docs/plan/check-srev-324.py`, `docs/plan/check-srev-324.sh`, ledger fragment, comment-only source clarification |
| Owner | `RpcRt_RpcStringBindingComposeW` historical disabled UserMgrCli note, with active policy owned by COM `ClosedClsid` |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`RpcRt_RpcStringBindingComposeW` currently owns one active local policy: SPP
callers are rewritten to `SPPCTransportEndpoint-00001` before forwarding to
`__sys_RpcStringBindingComposeW`. The adjacent UserMgrCli branch is disabled
source. Its old comment said the hook had to block a Windows 10 Explorer
right-click path, then said the actual Pin To Start Screen block moved to
`Com_CoCreateInstance`.

The active Pin To Start Screen policy is not in `rpcrt.c`. It is a COM class
policy:

```text
Sandboxie/install/Templates.ini [Template_WindowsExplorer]
  -> ClosedClsid={470C0EBD-5D73-4D58-9CED-E91E22E23282}
  -> Com_LoadClsidList("ClosedClsid")
  -> Com_IsClosedClsid
  -> Com_CoGetClassObject / Com_CoCreateInstance / Com_CoCreateInstanceEx
```

Related context menu interface hooking is separate:

```text
Com_CoCreateInstance -> IID_IContextMenu -> SH32_IContextMenu_Hook
  -> IContextMenuClsid setting
```

## Official Shape

Microsoft documents `RpcStringBindingComposeW` as composing a string binding
from object UUID, protocol sequence, network address, endpoint, and options. It
does not own COM class policy.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcstringbindingcomposew
```

Microsoft documents `CoCreateInstance` as creating a COM object instance from a
CLSID, class context, and requested interface. This is the correct layer for COM
class policy.

```text
https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cocreateinstance
```

Microsoft documents context menu handlers and `IContextMenu` as Shell extension
interfaces. Sandboxie's `IContextMenuClsid` hook is interface-level Shell
extension handling, not the same owner as the `ClosedClsid` deny policy.

```text
https://learn.microsoft.com/en-us/windows/win32/shell/context-menu-handlers
https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-icontextmenu
```

## Schema

Local schema:

```text
docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.schema.json
```

`RPCRT_DISABLED_USERMGRCLI_COM_POLICY_BOUNDARY` says:

- `RpcStringBindingComposeW` owns RPC string-binding composition and the local
  SPP endpoint rewrite before native forwarding;
- the UserMgrCli branch in `rpcrt.c` remains disabled historical source and
  must not become the active Pin To Start Screen policy owner;
- Pin To Start Screen blocking is owned by COM `ClosedClsid` loaded from
  templates/settings and enforced through `Com_IsClosedClsid` before COM class
  activation;
- `IContextMenuClsid` is a separate post-creation Shell interface hook;
- this SREV changes comments and proof only.

## Topology

```text
RPC caller
  -> RpcRt_RpcStringBindingComposeW
  -> optional SPP endpoint rewrite
  -> __sys_RpcStringBindingComposeW
```

```text
WindowsExplorer template
  -> ClosedClsid Pin To Start Screen CLSID
  -> Com_LoadClsidList
  -> Com_IsClosedClsid
  -> CoGetClassObject / CoCreateInstance / CoCreateInstanceEx deny gate
```

```text
CoCreateInstance success in Explorer
  -> IID_IContextMenu
  -> SH32_IContextMenu_Hook
  -> IContextMenuClsid post-creation hook
```

## Logic Risk

The old `rpcrt.c` comment mixed three layers: RPC string-binding composition,
COM class activation denial, and Shell context menu interface hooking. Because
the UserMgrCli branch is disabled, the comment could lead a future patch to
reactivate an RPC object-UUID deny as if it were the active COM policy. That
would move a COM class decision into the RPC string compose hook and bypass the
template-owned `ClosedClsid` contract.

## Fix

Comment-only source clarification. The `rpcrt.c` note now says SREV-324 keeps
the UserMgrCli RPC block inactive and that Pin To Start Screen is a COM
`ClosedClsid`/template policy, not an RPC compose policy.

No predicate, endpoint rewrite, disabled branch, COM class policy, template
setting, context menu hook, native RPC forwarding, or native COM forwarding
behavior changed.

## Acceptance Gate

`docs/plan/check-srev-324.py` validates the draft-07 schema, official Microsoft
references, source comment, inactive UserMgrCli branch, active SPP rewrite,
native `RpcStringBindingComposeW` forwarding, `Templates.ini` Pin To Start
Screen `ClosedClsid`, `Com_IsClosedClsid` enforcement before COM activation,
separate `IContextMenuClsid` hook path, stale Explorer hang wording removal,
and split ledger fragment.

Windows gate: Explorer context menu smoke with the WindowsExplorer template on
and off, proving Pin To Start Screen remains denied by `ClosedClsid` while the
disabled UserMgrCli RPC block remains inactive.
