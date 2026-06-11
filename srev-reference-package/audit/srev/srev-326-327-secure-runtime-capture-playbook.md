# SREV-326 / SREV-327: Secure Runtime Capture Playbook

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema |
| Input artifact | SREV-326, SREV-327, `Sandboxie/core/dll/secure.c`, Microsoft AccessCheckByType / GENERIC_MAPPING / SeAccessCheck / RPC binding handle / RPC_ASYNC_STATE documentation |
| Output artifact | `docs/plan/srev-326-327-secure-runtime-capture.schema.json`, `docs/plan/check-srev-326-327-secure-runtime-capture.py`, runtime capture checklist |
| Owner | secure.c runtime evidence contract for access-check bypass and AppInfo binding-handle probe |
| Acceptance gate | targeted checker validates source/spec adjacency and the evidence schema; Windows capture remains the runtime gate |

## Official Surface

SREV-326 and SREV-327 share a single rule: the local compatibility shortcut is
not the owner of the official semantic decision.

For `AccessCheckByType`, Microsoft documents that access is decided from the
security descriptor, token, optional object-type hierarchy, desired access, and
generic mapping. If `DesiredAccess == MAXIMUM_ALLOWED`, the result is the
maximum rights allowed by the security descriptor and token, not simply
`GenericAll`.

For AppInfo RPC elevation, Microsoft documents RPC binding handles as
runtime-owned opaque values and documents `RPC_ASYNC_STATE` as the async state
and notification shape. The binding-handle data structure is not an application
parsing contract. Microsoft also documents `RpcBindingInqObject` as the
supported route to return the object UUID associated with a binding handle.

Official references:

```text
https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-accesscheckbytype
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-generic_mapping
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-seaccesscheck
https://learn.microsoft.com/en-us/windows/win32/rpc/binding-handles
https://learn.microsoft.com/en-us/windows/win32/rpc/rpc-binding-handle
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindinginqobject
https://learn.microsoft.com/en-us/windows/win32/api/rpcasync/ns-rpcasync-rpc_async_state
https://learn.microsoft.com/en-us/windows/win32/api/rpcasync/ns-rpcasync-rpc_async_notification_info
```

Legal route:

```text
official API shape -> Windows runtime capture -> local compatibility decision
```

Illegal route:

```text
local allowlist/probe works once -> official semantics are satisfied
```

## Data

Each capture record must identify the shared runtime coordinates:

- Windows build, architecture, Sandboxie commit, box name, process image, user
  context, and capture tool.
- Feature path: `accesscheck-bypass` for SREV-326 or
  `appinfo-binding-probe` for SREV-327.
- Machine key: `feature path: `accesscheck-bypass``.
- Machine key: `feature path: `appinfo-binding-probe``.
- Route result: `bypass`, `native-forward`, `real-token-forward`,
  `probe-match`, `probe-miss`, `probe-exception`, or `rejected`.
- Evidence coordinates: trace/log path, debugger transcript, timestamp, and
  operator notes.

SREV-326 access-check records must include:

- Caller image class: Sandboxie BITS, Sandboxie WUAU, `wuauclt`, or
  non-allowlisted caller.
- Windows version gate: Windows 8.1 baseline and supported Windows 10/11.
- Desired access: specific access, generic-mapped access, and
  `MAXIMUM_ALLOWED`.
- Security descriptor class: allow DACL, deny DACL, NULL DACL, owner/group
  specific, and object-type-specific ACEs where `ObjectTypeList` is present.
- Token shape: sandboxed restricted token, real-token substitution path,
  non-admin token, admin token, and owner SID relation where relevant.
- Outputs: return status, `GrantedAccess`, `AccessStatus`, `LastError`,
  `PrivilegeSetLength`, and whether native `__sys_NtAccessCheckByType` ran.

SREV-327 AppInfo records must include:

- Call path: type-1 process elevation or type-2 token elevation.
- Async state fields: `RPC_ASYNC_STATE.Size`, `NotificationType`, `u.hEvent`,
  and whether `RpcNotificationTypeEvent` was accepted.
- Binding value class: null, small handle-like value, readable local pointer,
  unreadable pointer, or RPC handle-like opaque value.
- Probe outputs: `OFFSET_OF_BINDING_GUID`, GUID match/miss, exception code,
  guard-before-`memcmp` proof, elevation type, result handle slot, AppInfo call
  identity, and broker result.
- Machine evidence key: `BindingHandle value class`.

## Schema

Machine-readable capture records use:

```text
docs/plan/srev-326-327-secure-runtime-capture.schema.json
```

The schema accepts one record per runtime observation. A record can carry an
access-check payload, an AppInfo binding-probe payload, or both when the same
test case captures both paths.

## Topology

SREV-326:

```text
caller image + token + security descriptor
  -> Ldr_NtAccessCheckByType
  -> Ldr_TestToken/native NtAccessCheckByType
  -> allowlist fallback only if native API fails
  -> GrantedAccess / AccessStatus / LastError / return status
```

SREV-327:

```text
NdrAsyncClientCall
  -> Secure_CheckElevation
  -> RPC_ASYNC_STATE event gate
  -> RpcBindingInqObject official object UUID query
  -> BindingHandle value-class gate when official query fails
  -> fallback local GUID probe / exception path
  -> Secure_Elevation_Type and result handle slot
```

## Required Captures

SREV-326 positive and negative controls:

| Capture | Expected Proof |
|---|---|
| BITS/WUAU/WUAUCLT allowlist with current compatibility case | Native-first route and fallback shape are observable and explain compatibility need |
| Allowlisted native success | Must return native `GrantedAccess` / `AccessStatus` before fallback |
| Allowlisted native denial | Must return native denial before fallback |
| Allowlisted native API failure | Synthetic fallback may run and must be recorded |
| Non-allowlisted caller using same hook | Must reach `Ldr_TestToken` / native forwarding, not synthetic success |
| Deny DACL with allowlisted caller | Captures that native deny semantics are returned before fallback |
| NULL DACL and allow DACL | Output contract distinguishes compatibility success from native success |
| `MAXIMUM_ALLOWED` with `GenericMapping` | Records `GenericAll` synthetic grant and native comparison |
| Real-token substitution route | Proves non-bypass path still forwards the real token when applicable |

SREV-327 positive and negative controls:

| Capture | Expected Proof |
|---|---|
| AppInfo type-1 process elevation | Async state accepted, `RpcBindingInqObject` status and object UUID recorded, fallback binding value class recorded when used, result handle slot recorded |
| AppInfo type-2 token elevation | Same as above with token output slot |
| Non-AppInfo async RPC | Must not arm `Secure_Elevation_AsyncState` |
| Non-event notification type | Must be rejected before binding probe |
| Missing `u.hEvent` | Must be rejected before binding probe |
| Small binding value | Fallback guard must fire before `memcmp` |
| Unreadable binding pointer | Fallback `__try` exception path recorded |
| Readable pointer with mismatched GUID | Fallback probe miss recorded |

## Logic Risk

The two paths are different, but the failure mode is the same: a compatibility
shortcut may look green while bypassing the real Windows owner. Access-check
truth belongs to descriptor/token/object-type evaluation. RPC binding-handle
truth belongs to the RPC runtime. Any source change without these captures risks
turning a compatibility workaround into a semantic security hole.

## Acceptance Gate

Linux/source gate:

```bash
bash docs/plan/check-srev-326-327-secure-runtime-capture.sh
bash docs/plan/check-srev-326.sh
bash docs/plan/check-srev-327.sh
```

Windows gate:

1. Build Sandboxie service/DLL for the target architecture.
2. Capture SREV-326 access-check matrix on Windows 8.1+ and supported Windows
   10/11.
3. Capture SREV-327 AppInfo process and token elevation paths on supported
   Windows 10/11 x64 and WOW64 where applicable.
4. Store one JSON record per build/architecture/process/control.
5. Validate records against
   `docs/plan/srev-326-327-secure-runtime-capture.schema.json`.
6. Only after records validate may either bypass/probe behavior change.
