# SREV-300: IPC Self Impersonation Status Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/ipc.c`, SREV-110, Microsoft token query/duplicate/impersonation-level references |
| Output artifact | Self-impersonation status contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ipc_ImpersonateSelf`, `Ipc_NtImpersonateClientOfPort`, and `Ipc_NtAlpcImpersonateClientOfPort` |
| Acceptance gate | Targeted checker validates actual status return, ALPC comment topology, token duplicate/query shape, SREV-110 adjacency, stale wording removal, and ledger fragment |

## Data

`Ipc_NtImpersonateClientOfPort` and `Ipc_NtAlpcImpersonateClientOfPort` call the
native client-impersonation service first. For non-system sandboxed callers,
they then route through `Ipc_ImpersonateSelf`:

```text
native port impersonation
  -> Ipc_ImpersonateSelf
  -> existing thread token level check
  -> optional self primary-token duplicate to TokenImpersonation
  -> ThreadImpersonationToken install
```

`Ipc_ImpersonateSelf` already queries the existing thread token's
`TokenImpersonationLevel`. If the active token is already at
`SecurityImpersonation` or above, it returns success without changing the token.
Otherwise it clears active impersonation, opens this process token with
`TOKEN_DUPLICATE`, duplicates it into a `TokenImpersonation` token with
`TOKEN_IMPERSONATE | TOKEN_QUERY`, and installs that token on the current
thread.

Before this SREV, failure in the self-token path still returned
`STATUS_SUCCESS`. That made the wrapper report success even if no
`SecurityImpersonation` thread token was installed.

## Official Shape

Microsoft documents `NtQueryInformationToken(TokenImpersonationLevel)` as
returning a `SECURITY_IMPERSONATION_LEVEL` value for impersonation tokens and
failing if the token is not an impersonation token.

Microsoft documents `NtDuplicateToken` as creating either a primary token or an
impersonation token. The source token must have `TOKEN_DUPLICATE`; for
`TokenImpersonation`, the requested level is supplied through
`OBJECT_ATTRIBUTES.SecurityQualityOfService.ImpersonationLevel`; failures are
reported as NTSTATUS values such as `STATUS_BAD_IMPERSONATION_LEVEL` or
`STATUS_ACCESS_DENIED`.

Microsoft documents `SECURITY_IMPERSONATION_LEVEL`: `SecurityIdentification`
allows identity/privilege inspection but not local impersonation, while
`SecurityImpersonation` lets the server impersonate the client's security
context on the local system.

Microsoft documents `NtSetInformationThread` as returning `STATUS_SUCCESS` on
success or an NTSTATUS error on failure. `ThreadImpersonationToken` is an
internal/native thread information class in this source path; the local source
owns that use through existing `NtSetInformationThread` declarations.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryinformationtoken`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntduplicatetoken`
- `https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-security_impersonation_level`
- `https://learn.microsoft.com/de-de/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationthread`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psimpersonateclient`

## Schema

Local schema:

```text
docs/plan/srev-300-ipc-self-impersonation-status-gate.schema.json
```

Contract id:

```text
IPC_SELF_IMPERSONATION_STATUS_GATE
```

## Boundary

```text
Native LPC/ALPC impersonation result
  -> Ipc_ImpersonateSelf policy
  -> active SecurityImpersonation token or duplicated self token
  -> wrapper NTSTATUS result
```

`Ipc_ImpersonateSelf` owns the post-native fallback status. A success result is
legal only when an existing `SecurityImpersonation` token is preserved or the
self-token duplicate/install path succeeds.
`Ipc_ImpersonateSelf must return the actual self-impersonation status` is the
local invariant that keeps wrapper success aligned to the token state.

## Topology

```text
Thread token query
  -> if ImpLevel >= SecurityImpersonation: return STATUS_SUCCESS
  -> else clear current impersonation
  -> open process token TOKEN_DUPLICATE
  -> NtDuplicateToken(... TokenImpersonation ...)
  -> NtSetInformationThread(ThreadImpersonationToken)
  -> return actual status
```

SREV-110 owns the adjacent driver-side private-offset token replay shim.
SREV-300 owns the DLL-side user-mode/native fallback status contract for LPC
and ALPC client impersonation.

## Logic Risk

The old code conflated "we want the caller path to continue" with "a legal
impersonation state exists." Returning `STATUS_SUCCESS` after
`NtOpenProcessToken`, `NtDuplicateToken`, or `NtSetInformationThread` failed
could push the caller into later work while still lacking a usable
`SecurityImpersonation` token. That is exactly the case described by the
existing comment: identification-level impersonation can later surface as
`STATUS_BAD_IMPERSONATION_LEVEL`.

## Fix

`Ipc_ImpersonateSelf` now returns the actual status from the self-impersonation
path. Existing fast-path success for already-usable impersonation tokens is
unchanged. On failure, the function still attempts to restore the old thread
token before returning the failure status.

The ALPC source comment now names the SREV-300 topology and says success means
`Ipc_ImpersonateSelf` actually installed a self `SecurityImpersonation` token
or preserved an existing one. No token access mask, impersonation level,
RPCSS/admin exception, native call, or system-SID bypass changed.

## Acceptance Gate

`docs/plan/check-srev-300.py` validates the draft-07 schema, official
references, source status return, unchanged token query/duplicate/install
shape, restore-on-error path, system-SID bypass preservation, SREV-110
adjacency, stale wording removal, combined ledger entry, and split ledger
fragment.

Runtime gate: Windows LPC/ALPC impersonation smoke covering successful native
client impersonation, identification-level native result followed by successful
self-token install, forced `NtDuplicateToken`/`NtSetInformationThread` failure
returning a failure status, and RPCSS/admin exception behavior.
