# SREV-327: Secure AppInfo Binding Handle Layout Probe

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/secure.c`, `Sandboxie/core/dll/rpcrt.c`, Microsoft RPC binding handle and async RPC references |
| Output artifact | `docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.schema.json`, `docs/plan/check-srev-327.py`, `docs/plan/check-srev-327.sh`, ledger fragment, source-level official RPC object UUID query with compatibility fallback |
| Owner | `Secure_CheckElevation` AppInfo RPC elevation detector |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`Secure_CheckElevation` detects UAC elevation calls by recognizing a
`NdrAsyncClientCall` argument shape used to contact the AppInfo service. It
checks:

```text
Args
AsyncState
RPC_ASYNC_STATE size 0x44 / 0x70
RpcNotificationTypeEvent
AsyncState->u.hEvent
Args->BindingHandle
RpcBindingInqObject object UUID query
binding GUID bytes at OFFSET_OF_BINDING_GUID
output process/token handle slots
```

The source now tries the official RPC binding route first: call
`RpcBindingInqObject` on `Args->BindingHandle` and compare the returned object
UUID with the known AppInfo elevation UUIDs. If the RPC runtime does not
classify the value as a binding, the compatibility fallback casts
`Args->BindingHandle` to `UCHAR *`, rejects null and very small values, and
reads a GUID at the fixed local offset. The old comment admitted that the name
`BindingHandle` implies a handle, while the code treated it only as a memory
pointer; it also said Windows 10 sometimes passes real handles and that the
small-value filter is a hack.

## Official Shape

Microsoft documents RPC binding handles as information owned by the RPC runtime
library. Applications pass binding handles to runtime APIs; they do not directly
access the data structure behind the handle.

```text
https://learn.microsoft.com/en-us/windows/win32/rpc/binding-handles
https://learn.microsoft.com/en-us/windows/win32/rpc/rpc-binding-handle
```

Microsoft documents `RpcBindingFromStringBinding` as returning a binding handle
from a string binding and says the binding handle should later be released with
`RpcBindingFree`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindingfromstringbinding
```

Microsoft documents `RpcBindingInqObject` as returning the object UUID from a
client or server binding handle. It returns `RPC_S_INVALID_BINDING` when the
binding handle is invalid.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindinginqobject
```

Microsoft documents `RPC_ASYNC_STATE` as the client-allocated async call state.
It includes a `NotificationType` and notification union; runtime-owned fields
such as `RuntimeInfo` are reserved and not an application parsing surface.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcasync/ns-rpcasync-rpc_async_state
```

Microsoft documents `RPC_NOTIFICATION_TYPES`, including
`RpcNotificationTypeEvent`, as the async call notification mechanism.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcasync/ne-rpcasync-rpc_notification_types
```

## Schema

Local schema:

```text
docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.schema.json
```

`SECURE_APPINFO_BINDING_HANDLE_LAYOUT_PROBE` says:

- official RPC binding handles are opaque RPC runtime objects, not structures
  Sandboxie may parse by contract;
- `RpcBindingInqObject` is the supported first route for reading an object UUID
  from a binding handle;
- `RPC_ASYNC_STATE` owns only the documented async state and notification shape;
- `Secure_CheckElevation` uses the official object-UUID query first and keeps
  the local observed AppInfo binding layout probe only as a compatibility
  fallback;
- the fixed `OFFSET_OF_BINDING_GUID` values are local evidence, not official
  Microsoft binding-handle ABI;
- the fallback must keep the small-handle guard before any fixed-offset GUID
  read;
- runtime proof must classify `BindingHandle` and record whether the official
  object UUID query or fallback layout probe matched before changing offsets,
  guards, GUID comparison, or `__try` exception behavior.

## Topology

```text
NdrAsyncClientCall stack
  -> RpcRt_NdrAsyncClientCall / Secure_CheckElevation handoff
  -> Secure_CheckElevation
  -> RPC_ASYNC_STATE shape gate
  -> RpcBindingInqObject official object UUID query
  -> if invalid binding: local pointer/small-handle gate
  -> fallback fixed-offset binding GUID probe
  -> elevation type/result handle capture
```

The local probe now sits behind the official RPC API shape. Future behavior
changes must preserve that priority: official binding-handle API first, fixed
offset layout probe only as a compatibility fallback with version-specific
runtime proof. The fallback remains not official RPC handle shape.

## Logic Risk

The old comment named the right concern but left it as an inline complaint. The
source read through a value named `BindingHandle`, which official RPC docs say
is runtime-owned. The new first path asks the RPC runtime for the object UUID
instead of parsing binding-handle storage. The fallback `ptr < 0x1fff` guard
still avoids obvious small real handles, but it does not prove the remaining
value is a safe, readable binding layout. Because the code is inside `__try`,
invalid reads are caught, but that does not make the fixed-offset fallback a
documented contract.

## Runtime Capture Matrix

The Windows gate is not "does UAC still work". It must prove the observed
AppInfo binding layout across the crossing that Sandboxie is currently
probing.

Shared secure runtime capture playbook:

```text
docs/plan/srev-326-327-secure-runtime-capture-playbook.md
```

Machine-readable evidence schema:

```text
docs/plan/srev-326-327-secure-runtime-capture.schema.json
```

Required dimensions:

- Windows builds: supported Windows 10 and Windows 11 releases, with build
  number and architecture recorded.
- Architecture: x64 process and WOW64 process where supported.
- AppInfo call path: type-1 process elevation and type-2 token elevation.
- Async state: `RPC_ASYNC_STATE.Size`, `NotificationType`,
  `u.hEvent`, and whether `RpcNotificationTypeEvent` is the only accepted
  path.
- Binding value class: null, small real-handle-like value, readable local
  pointer, unreadable pointer, and official RPC handle-like value if observed.
- Probe result: `RpcBindingInqObject` status, returned object UUID, official
  object UUID match/miss, fallback `OFFSET_OF_BINDING_GUID`, fallback GUID
  match/miss, exception code from the `__try` path, and whether the fallback
  guard fired before `memcmp`.
- Output capture: elevation type, result handle slot, process image, AppInfo
  endpoint/call identity, and final broker result.

Negative controls:

- non-AppInfo async RPC call through `NdrAsyncClientCall`;
- AppInfo call with `NotificationType` other than `RpcNotificationTypeEvent`;
- null or missing `u.hEvent`;
- binding value below the fallback small-handle guard;
- readable pointer with mismatched GUID;
- unreadable page at the binding pointer;
- ordinary non-elevation RPC path that should not arm
  `Secure_Elevation_AsyncState`.

## Fix

Source-level official API first path. `Secure_CheckElevation` now calls
`RpcBindingInqObject` to query the binding-handle object UUID before using the
observed AppInfo memory-layout probe. If `RpcBindingInqObject` succeeds, its
object UUID result decides the binding match. If it fails or is unavailable,
the old fixed-offset memory probe remains as a compatibility fallback with the
small-handle guard kept before the `memcmp`.

No async-state predicate, notification gate, GUID byte offset, elevation type
detection, output handle capture, exception handling, or service request
behavior changed. The local pointer cast, small-handle guard, and `memcmp`
remain only on the fallback route.

## Acceptance Gate

`docs/plan/check-srev-327.py` validates the draft-07 schema, official Microsoft
references, `RpcBindingInqObject` official object UUID query, preserved
async-state gates, preserved 32/64-bit binding GUID offsets, fallback
small-handle guard before fallback `memcmp`, preserved type-1/type-2 elevation
detection, stale hack wording removal, combined ledger entry, and split ledger
fragment.
`docs/plan/check-srev-326-327-secure-runtime-capture.sh` validates the shared
secure runtime capture playbook and machine-readable evidence schema.

Windows gate: capture AppInfo UAC elevation calls on supported Windows versions,
including Windows 10/11 and x64/WOW64 where supported, and prove whether
`BindingHandle` is accepted through the official object UUID route, a readable
local layout pointer fallback, a small handle-like value, or varies by build
before release. The capture must record async-state fields,
`RpcBindingInqObject` status, object UUID result, fallback pointer guard result,
fallback GUID probe result, `__try` exception path, elevation type, result
handle slot, process image, AppInfo call identity, and negative controls.
