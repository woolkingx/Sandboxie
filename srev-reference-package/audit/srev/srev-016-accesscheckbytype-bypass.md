# SREV-016 AccessCheckByType Bypass Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents `AccessCheckByType` as an authorization API that compares a
security descriptor with a client token and reports whether the requested access
is granted.

Important output contracts:

- `DesiredAccess` is the access mask to check and should already have generic
  rights mapped.
- If `DesiredAccess` is `MAXIMUM_ALLOWED`, `GrantedAccess` indicates the maximum
  access rights allowed by the security descriptor.
- `GenericMapping->GenericAll` should contain all rights grantable by the
  resource manager.
- If `AccessStatus` is `FALSE`, `GrantedAccess` is set to zero.
- If the function fails, output masks are not set.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-accesscheckbytype
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-accesscheck

## Local Risk

Sandboxie has compatibility bypasses for BITS/WUAU-related images that set:

```c
GrantedAccess = 0xFFFFFFFF
AccessStatus = TRUE
```

This preserves compatibility but reports rights broader than the caller
requested and broader than any local resource-manager mapping. The native
`NtAccessCheckByType` hook also returned `TRUE` as an `NTSTATUS`, which is
success-like but not `STATUS_SUCCESS`.

## Patch Boundary

This patch keeps the existing compatibility bypass scope. It only constrains the
reported access shape:

- normal desired access: report `DesiredAccess`
- `MAXIMUM_ALLOWED`: report `GenericMapping->GenericAll` plus non-maximum bits
  when a mapping exists
- NT hook returns `STATUS_SUCCESS`

Runtime compatibility for BITS/WUAU still needs Windows smoke before this can be
treated as behavior-verified.

## Acceptance Gate

- No AccessCheckByType bypass reports `0xFFFFFFFF`.
- Win32 bypass returns `TRUE` with `AccessStatus = TRUE`.
- NT bypass returns `STATUS_SUCCESS` with `AccessStatus = STATUS_SUCCESS`.
- Runtime gate remains open for BITS/WUAU behavior.
