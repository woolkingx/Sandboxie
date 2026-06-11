# SREV-110: Thread Impersonation Offset Boundary

## Data

`Sandboxie/core/drv/thread.c` is the highest-risk file in the unnamed core-file
queue after uncovered comment risks reached zero. The risk is concentrated in
thread token replay and cross-process/thread access filtering:

```text
Thread_SetThreadToken
  -> choose stored thread impersonation token or process primary token
  -> Thread_MyImpersonateClient

Thread_StoreThreadToken
  -> PsReferenceImpersonationToken
  -> store the referenced token in THREAD::token_object

Thread_MyImpersonateClient
  -> PsImpersonateClient(..., SecurityIdentification)
  -> patch the locally known ETHREAD client-security field to the recorded level
  -> fail closed if the dynamic offset does not point at TokenObject
```

This is not a normal public API wrapper. It is an intentional Sandboxie
compatibility shim over private `ETHREAD` layout data supplied by dynamic-data
configuration. It exists because sandboxed process primary tokens are heavily
restricted, while some syscalls need the original caller token context during
dispatch.

## Official Shape

Microsoft documents `PsImpersonateClient` as assigning a token to a server
thread with `CopyOnOpen`, `EffectiveOnly`, and `SECURITY_IMPERSONATION_LEVEL`
inputs. Passing `NULL` as the token ends impersonation. Microsoft also
documents that if the server thread is already impersonating, the previous token
reference count is decremented, and drivers should call
`PsReferenceImpersonationToken` before replacing impersonation if they need to
preserve the token.

Microsoft documents the important gate: `PsImpersonateClient` checks conditions
including token authentication/SID/restricted-token shape. If the conditions are
not met, it can copy the token and assign the copy with a limited impersonation
level where the server thread can only obtain information about the client.

Microsoft warns that raising the privilege state of an untrusted user thread is
extremely unsafe, and says higher-privilege work should be dispatched to a
system worker thread when that is the required design. `PsImpersonateClient`,
`PsReferenceImpersonationToken`, and `PsRevertToSelf` are all documented at
`PASSIVE_LEVEL`.

Microsoft documents `SECURITY_IMPERSONATION_LEVEL`: `SecurityIdentification`
allows identity and privilege inspection but not impersonation, while
`SecurityImpersonation` lets the server impersonate the client's security
context on the local system.

Microsoft documents the `SeImpersonatePrivilege` user right as the policy that
allows a program to impersonate a user or another account after authentication.
The same article says lower requested levels such as Anonymous or Identify are
allowed without that user right in the common policy model.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psimpersonateclient
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psreferenceimpersonationtoken
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psreverttoself
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_security_impersonation_level
https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/security-policy-settings/impersonate-a-client-after-authentication
```

## Schema

Local schema:

```text
docs/plan/srev-110-thread-impersonation-offset-boundary.schema.json
```

The thread impersonation offset contract is:

```text
Thread_StoreThreadToken references the active impersonation token before storage
stored thread tokens keep CopyOnOpen EffectiveOnly and local SecurityImpersonation replay level
Thread_SetThreadToken replays a stored thread token or the process primary token for syscall dispatch
Thread_MyImpersonateClient calls PsImpersonateClient at SecurityIdentification first
the ETHREAD client-security field update is private dynamic-data owned state
Vista and later validate the masked client-security pointer against TokenObject before writing level bits
XP validates the PS_IMPERSONATION_INFORMATION TokenObject before writing ImpersonationLevel
offset mismatch returns STATUS_ACCESS_DENIED and logs MSG_1222 0x62
this SREV must not replace the shim with direct SecurityImpersonation or worker-thread dispatch
runtime proof is required for each supported Windows build dynamic-data offset
```

## Topology

Token capture topology:

```text
PsReferenceImpersonationToken(PsGetCurrentThread)
  -> returns referenced TokenObject plus CopyOnOpen EffectiveOnly ImpersonationLevel
  -> proc->threads_lock
  -> THREAD::token_object = TokenObject
  -> THREAD::token_CopyOnOpen = CopyOnOpen
  -> THREAD::token_EffectiveOnly = EffectiveOnly
  -> THREAD::token_ImpersonationLevel = SecurityImpersonation
  -> old token dereferenced after lock release
```

Token replay topology:

```text
Thread_SetThreadToken
  -> read THREAD::token_object under proc->threads_lock
  -> reference stored token when present
  -> otherwise use proc->primary_token
  -> Thread_MyImpersonateClient(PsGetCurrentThread, TokenObject, flags, level)
  -> dereference transient stored-token reference
```

Private offset topology:

```text
Thread_MyImpersonateClient
  -> PsImpersonateClient(..., SecurityIdentification)
  -> Dyndata_Config.ImpersonationData_offset
  -> XP: PS_IMPERSONATION_INFORMATION.TokenObject must equal TokenObject
  -> Vista+: (*ClientSecurity & ~7) must equal TokenObject, or the next pointer-sized slot must match
  -> update only the impersonation level bits/field
  -> on mismatch: STATUS_ACCESS_DENIED + MSG_1222/0x62
```

## Logic Risk

The old comment described this as a workaround, but did not name the hard
boundary. The code is intentionally outside the public DDI contract because the
public `PsImpersonateClient` semantics can downgrade a sandboxed caller to
`SecurityIdentification`. The local legality comes from dynamic-data ownership
of the private offset and from fail-closed pointer verification before changing
the level.

Replacing this with a direct `PsImpersonateClient(..., SecurityImpersonation)`
call would likely restore the official downgrade behavior the shim is avoiding.
Replacing it with a system worker-thread design would be an architecture change
across syscall dispatch, token replay, and object access checks. That may be a
future hardening direction, but it is not a source-local fix.

## Fix

Comment-only source clarification: the source now names the path as a Sandboxie
compatibility shim, states that supported API semantics can downgrade the
sandboxed caller to `SecurityIdentification`, states that the ETHREAD
client-security update is based on locally known dynamic data, and names the
fail-closed offset verification rule.

No token capture, token reference, impersonation call, private offset, failure
status, process termination, object access filter, or syscall hook behavior
changed.

## Acceptance Gate

`docs/plan/check-srev-110.py` validates the draft-07 schema, official
references, token capture/replay topology, private offset verification for XP
and Vista+ paths, failure status/logging, source comment clarification, absence
of a direct `SecurityImpersonation` `PsImpersonateClient` replacement, and
ledger entry. `docs/plan/check-srev-110.sh` is the matrix wrapper.

Runtime gate: Windows matrix over each supported build dynamic-data offset,
thread token capture through `NtImpersonateAnonymousToken` /
`NtImpersonateClientOfPort`, syscall dispatch requiring original token context,
offset mismatch fail-closed observation, Driver Verifier, HVCI where supported,
and object access filter behavior before and after `Thread_SetThreadToken`.
