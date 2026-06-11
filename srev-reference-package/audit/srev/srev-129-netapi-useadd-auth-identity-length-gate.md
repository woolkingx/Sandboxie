# SREV-129: NetApi UseAdd Auth Identity Length Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/netapiserver.cpp`, `Sandboxie/core/svc/netapiwire.h`, `Sandboxie/core/dll/netapi.c`, Microsoft NetUseAdd / USE_INFO references |
| Output artifact | `docs/plan/srev-129-netapi-useadd-auth-identity-length-gate.schema.json`, `docs/plan/check-srev-129.py`, `docs/plan/check-srev-129.sh`, ledger row |
| Owner | `NetApiServer::UseAdd` in `Sandboxie/core/svc/netapiserver.cpp` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows NetUseAdd broker runtime remains required |

## Evidence

`Sandboxie/core/svc/netapiserver.cpp` was the highest-ranked unnamed reviewable core file after SREV-128. `NetApiServer::UseAdd` receives a fixed `NETAPI_USE_ADD_REQ` wire packet, converts its local fields into a `USE_INFO_*` view, impersonates the caller, calls `NetUseAdd(NULL, req->level, (UCHAR *)&info, &parm_index)`, then starts the drive notification slave only on success.

For string fields, invalid lengths set `parm_index` and the code exits before impersonation. For `ui4_auth_identity_length`, the old code set `error_code = ERROR_INVALID_PARAMETER` when the length was greater than the fixed 2048 byte wire buffer, but did not exit. The later `PipeServer::ImpersonateCaller()` and `NetUseAdd()` path overwrote `error_code` and consumed a partially initialized `USE_INFO_4`.

Microsoft documents `NetUseAdd` as receiving a `buf` whose format depends on the Level parameter and returning `ERROR_INVALID_PARAMETER` with `parm_err` naming the invalid `USE_INFO_*` member. Microsoft documents `USE_INFO_2` string members such as local, remote, password, username, and domain name as pointer fields consumed by the API. Microsoft documents `USE_INFO_3` as nesting `USE_INFO_2` and adding `ui3_flags`. The local Sandboxie level-4 extension follows that same data-to-pointer topology and must reject impossible wire sizes before the NetAPI call.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/lmuse/nf-lmuse-netuseadd
- https://learn.microsoft.com/en-us/windows/win32/api/lmuse/ns-lmuse-use_info_2
- https://learn.microsoft.com/en-us/windows/win32/api/lmuse/ns-lmuse-use_info_3

## Data

`NetApiServer::UseAdd`, `NETAPI_USE_ADD_REQ`, `NETAPI_USE_ADD_RPL`, `req->level`, `ui4_auth_identity_length`, `ui4_auth_identity[2048+2]`, local `USE_INFO_4`, `error_code`, `parm_index`, `PipeServer::ImpersonateCaller`, `NetUseAdd`, `LaunchSlave`, and client-side `NetApi_NetUseAdd`.

## Schema

`NETAPI_USEADD_AUTH_IDENTITY_LENGTH_GATE` says:

- `UseAdd` validates every `NETAPI_USE_ADD_REQ` wire field before `PipeServer::ImpersonateCaller` or `NetUseAdd` can run.
- `ui4_auth_identity_length` uses the `NETAPI_USE_ADD_REQ` fixed 2048 byte wire buffer limit.
- `ui4_auth_identity_length == ULONG -1` remains the null auth identity sentinel.
- `ui4_auth_identity_length > 2048` sets `ERROR_INVALID_PARAMETER` and exits before impersonation.
- Valid `ui4_auth_identity` bytes are locally terminated before `USE_INFO_4` points at the wire buffer.
- `parm_index` based string length failures still return `ERROR_INVALID_PARAMETER` before impersonation.
- `NetUseAdd` receives only a `USE_INFO` shaped buffer assembled from validated local wire fields.
- `LaunchSlave` still runs only after `NetUseAdd` succeeds.
- NetUseAdd level policy, local string limits, password handling, and drive notification topology are unchanged.

## Topology

The legal broker path is:

```text
NETAPI_USE_ADD_REQ fixed wire packet
  -> validate h.length and level
  -> validate/cap local remote password username domain auth_identity
  -> assemble USE_INFO_* pointer view into local wire buffers
  -> PipeServer::ImpersonateCaller
  -> NetUseAdd
  -> NETAPI_USE_ADD_RPL
  -> optional LaunchSlave only on success
```

The corrected invalid-auth path is:

```text
level >= 4 and ui4_auth_identity_length > 2048
  -> error_code = ERROR_INVALID_PARAMETER
  -> finish reply
  -> no impersonation
  -> no NetUseAdd
```

## Logic Risk

The old code treated `error_code` as if setting it was a control-flow gate, but the later code overwrote it with impersonation and `NetUseAdd` results. That let a caller submit a wire value that cannot fit the declared fixed buffer and still cross the broker boundary into a real network management API call. Because `USE_INFO_4` is a local stack view, skipping its valid branch also leaves the auth identity pointer/length members outside their legal initialization state.

The correct repair is a local validation barrier before impersonation, not a change to NetUseAdd policy, string length limits, or slave launch behavior.

## Fix

`NetApiServer::UseAdd` now checks `if (error_code) goto finish;` after the level-4 field validation and before the existing `parm_index` gate. Invalid `ui4_auth_identity_length > 2048` therefore returns `ERROR_INVALID_PARAMETER` without impersonating the caller or calling `NetUseAdd`. Valid auth identity data and the `ULONG -1` null sentinel behavior remain unchanged.

## Acceptance Gate

`docs/plan/check-srev-129.py` validates the draft-07 schema, official references, wire shape, client request construction precedent, invalid auth identity length gate before impersonation, existing `parm_index` gate preservation, valid auth identity termination and pointer assignment, `NetUseAdd` call topology, success-only `LaunchSlave`, stale ungated pattern removal, and ledger entry. `docs/plan/check-srev-129.sh` is the matrix wrapper.

Runtime/build gate: Windows service build for `netapiserver.cpp`, valid `NetUseAdd` mapping smoke, malformed level-4 request with `ui4_auth_identity_length = 2049` proving no `NetUseAdd` call and `ERROR_INVALID_PARAMETER`, null sentinel request proving unchanged behavior, and 2048-byte valid auth identity request proving unchanged forwarding.
