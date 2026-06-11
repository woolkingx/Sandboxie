# SREV-326: Secure BITS/WUAU AccessCheckByType Bypass

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/secure.c`, Microsoft AccessCheckByType / GENERIC_MAPPING / SeAccessCheck references |
| Output artifact | `docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.schema.json`, `docs/plan/check-srev-326.py`, `docs/plan/check-srev-326.sh`, ledger fragment, native-access-check-first source path |
| Owner | `Ldr_NtAccessCheckByType` BITS/WUAU compatibility bypass |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`Ldr_NtAccessCheckByType` intercepts access checks, optionally swaps a sandboxed
token for the real token through `Ldr_TestToken`, then forwards to
`__sys_NtAccessCheckByType`.

Windows 8.1+ has a local allowlist:

```text
Dll_ImageType == DLL_IMAGE_SANDBOXIE_BITS
Dll_ImageType == DLL_IMAGE_SANDBOXIE_WUAU
Dll_ImageType == DLL_IMAGE_WUAUCLT
```

For those images the source now tries the native access check first with the
same real-token route used by non-allowlisted callers. Only if the native API
itself fails does it fall back to the synthetic compatibility grant:

```text
granted_access = DesiredAccess
if DesiredAccess has MAXIMUM_ALLOWED and GenericMapping exists:
  granted_access = GenericMapping->GenericAll | (DesiredAccess & ~MAXIMUM_ALLOWED)
*GrantedAccess = granted_access
*AccessStatus = STATUS_SUCCESS
SetLastError(0)
return STATUS_SUCCESS
```

## Official Shape

Microsoft documents `AccessCheckByType` as checking a security descriptor
against an impersonation token, optional `OBJECT_TYPE_LIST`, and
`GENERIC_MAPPING`. `DesiredAccess` must have generic access mapped by
`MapGenericMask`; if it is `MAXIMUM_ALLOWED`, the function sets
`GrantedAccess` to the maximum rights the security descriptor allows.

```text
https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-accesscheckbytype
```

Microsoft documents `GENERIC_MAPPING` as the object-type mapping from generic
access rights to object-specific and standard access rights.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-generic_mapping
```

Microsoft documents `SeAccessCheck` as the kernel security routine that checks
requested access against a security descriptor and subject context. It records
that `MAXIMUM_ALLOWED` performs DACL checks, may perform privilege/owner tests,
and that a failed check should return the specific `AccessStatus`.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-seaccesscheck
```

No public Microsoft Win32 API page was found for `NtAccessCheckByType` during
this pass. This SREV therefore uses `AccessCheckByType` and `SeAccessCheck` as
the official semantic baseline, while treating `Ldr_NtAccessCheckByType`'s
native target as local ntdll hook evidence.

## Schema

Local schema:

```text
docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.schema.json
```

`SECURE_BITS_WUAU_ACCESSCHECK_BYPASS` says:

- official access-check semantics are descriptor/token/object-type/generic
  mapping decisions;
- `MAXIMUM_ALLOWED` is not equivalent to blindly granting `GenericAll`;
- the BITS/WUAU branch is a local compatibility bypass, not a proven access
  check implementation;
- the bypass is limited to BITS, Sandboxie WUAU, and `wuauclt`;
- allowlisted callers must try `Ldr_TestToken` plus native
  `__sys_NtAccessCheckByType` before using the synthetic compatibility grant;
- all other callers must continue through `Ldr_TestToken` and native
  `__sys_NtAccessCheckByType`;
- the synthetic `MAXIMUM_ALLOWED -> GenericAll` fallback is allowed only when
  the native API call itself fails.

## Topology

Normal route:

```text
caller
  -> Ldr_NtAccessCheckByType
  -> Ldr_TestToken(ClientToken, real token)
  -> __sys_NtAccessCheckByType
  -> native descriptor/token access decision
```

Allowlisted route:

```text
Windows 8.1+ BITS/WUAU/WUAUCLT image
  -> Ldr_NtAccessCheckByType
  -> Ldr_TestToken(ClientToken, real token)
  -> __sys_NtAccessCheckByType
  -> if native call succeeds: native descriptor/token access decision
  -> if native call fails: synthetic compatibility grant
```

## Logic Risk

The old branch was indeed not equivalent to documented access-check semantics:
it ignored the security descriptor, token groups, privileges, owner checks,
object-type hierarchy, and denial-specific `AccessStatus`. The source now
restores the owner order for allowlisted callers: native
descriptor/token/object-type access check first, synthetic compatibility grant
only if the native API call itself fails. This does not prove BITS/WUAU
compatibility on Windows, but it removes the unconditional skip over native
access semantics.

## Runtime Verification Matrix

The Windows gate must prove both the compatibility need and the security
boundary before this bypass can be changed:

Shared secure runtime capture playbook:

```text
docs/plan/srev-326-327-secure-runtime-capture-playbook.md
```

Machine-readable evidence schema:

```text
docs/plan/srev-326-327-secure-runtime-capture.schema.json
```

| Axis | Required coverage |
|---|---|
| Windows versions | Windows 8.1 baseline plus supported Windows 10/11 builds |
| Allowlist callers | `DLL_IMAGE_SANDBOXIE_BITS`, `DLL_IMAGE_SANDBOXIE_WUAU`, and `DLL_IMAGE_WUAUCLT` paths that currently need the bypass |
| Non-allowlist callers | at least one sandboxed non-BITS/WUAU caller using the same hook path must continue through `Ldr_TestToken` and native `__sys_NtAccessCheckByType` |
| Desired access | specific requested access, generic-mapped access after `MapGenericMask`, and `MAXIMUM_ALLOWED` |
| Security descriptors | allow DACL, deny DACL, NULL DACL, owner-only or group-specific DACL, and object-type-specific ACEs when `ObjectTypeList` is present |
| Token shape | sandboxed restricted token, real-token substitution path, non-admin token, and admin token where applicable |
| Expected native-first evidence | allowlisted callers take the native result when `__sys_NtAccessCheckByType` succeeds, including deny descriptors |
| Expected fallback evidence | allowlisted callers keep the compatibility behavior needed by BITS/WUAU when the native API call itself fails |
| Expected negative evidence | non-allowlisted callers and deny descriptors do not inherit the synthetic success path |
| Output contract | `GrantedAccess`, `AccessStatus`, `SetLastError`, and return status are recorded for bypass, native success, and native denial |
| Regression | normal `Ldr_TestToken` and native forwarding behavior remain unchanged for all non-allowlisted callers |

Do not treat `MAXIMUM_ALLOWED -> GenericAll` as a correct access-check model.
It is only the current allowlisted compatibility behavior until the matrix
proves a safer policy.

## Fix

Source-level native-first access-check path. The allowlisted BITS/WUAU/WUAUCLT
branch now calls `Ldr_TestToken` and `__sys_NtAccessCheckByType` before any
synthetic grant. If the native API succeeds, its descriptor/token/object-type
result is returned. If the native API itself fails, the old synthetic
`MAXIMUM_ALLOWED -> GenericAll` compatibility behavior remains as the fallback.

No image predicate, OS-build gate, fallback `MAXIMUM_ALLOWED` handling,
fallback `GrantedAccess` assignment, fallback `AccessStatus`, fallback
`SetLastError`, non-allowlisted `Ldr_TestToken`, or non-allowlisted native
forwarding behavior changed.

## Acceptance Gate

`docs/plan/check-srev-326.py` validates the draft-07 schema, official Microsoft
references, source comment, unchanged BITS/WUAU/WUAUCLT allowlist, unchanged
fallback `MAXIMUM_ALLOWED`/`GenericAll` synthetic grant, native access-check
first ordering for allowlisted callers, preserved non-allowlisted
`Ldr_TestToken` and native forwarding fallback, stale uncertainty comment
removal, combined ledger entry, and split ledger fragment.

The source gate explicitly proves native access-check first ordering before the
synthetic fallback.
`docs/plan/check-srev-326-327-secure-runtime-capture.sh` validates the shared
secure runtime capture playbook and machine-readable evidence schema.

Windows gate: run the runtime verification matrix above before release. The
matrix must prove that BITS/WUAU compatibility is preserved, native success and
native deny results are returned before fallback, and non-allowlisted callers
plus deny-descriptor cases do not inherit synthetic success.
Machine evidence key: `non-allowlisted callers plus deny-descriptor cases`.
