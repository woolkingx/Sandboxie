# SREV-183 Token Handle DACL Status Gate

## Data

Owner file:

```text
Sandboxie/core/drv/token.c
```

Reviewed public declaration surface:

```text
Sandboxie/core/drv/token.h
```

Reviewed nodes:

```text
Token_FilterDacl
Token_SetHandleDacl
TOKEN_DEFAULT_DACL
ACL
RtlCreateSecurityDescriptor
RtlSetDaclSecurityDescriptor
ZwSetSecurityObject
DACL_SECURITY_INFORMATION
```

## Schema

`TOKEN_HANDLE_DACL_STATUS_GATE` defines these local contracts:

- `Token_FilterDacl` owns the restricted-token DACL update route after token filtering.
- `Token_SetHandleDacl` builds an absolute security descriptor for an existing DACL and applies it to a token, process, or thread handle.
- Security descriptor construction DDIs return `NTSTATUS`; failure must stop before `ZwSetSecurityObject`.
- `RtlSetDaclSecurityDescriptor` references the supplied ACL; the local route must pass the non-NULL ACL already built by `Token_FilterDacl`.
- `ZwSetSecurityObject(DACL_SECURITY_INFORMATION)` is the only executor that mutates the target object's DACL in this helper.
- This SREV does not change token filtering policy, SID selection, default-DACL sizing, object targets, handle ownership, or access masks.
- Windows build and runtime proof are required because this workspace cannot compile or load the driver.

## Topology

The local path is:

```text
Token_Filter
  -> Token_FilterDacl
  -> Token_Query(TokenUser)
  -> Token_Query(TokenDefaultDacl)
  -> build x_dacl_ptr
  -> ObOpenObjectByPointer(OBJ_KERNEL_HANDLE)
  -> Token_SetHandleDacl(TokenHandle, x_dacl_ptr)
  -> Token_SetHandleDacl(NtCurrentProcess(), x_dacl_ptr)
  -> Token_SetHandleDacl(NtCurrentThread(), x_dacl_ptr)
  -> ZwSetSecurityObject(DACL_SECURITY_INFORMATION)
```

`Sandboxie/core/drv/token.h` exposes the token owner API surface. The DACL helper
itself is private to `token.c`, so the legal patch boundary is the private
helper and its source-level proof, not a public header contract change.

## Logic Risk

Before this SREV, `Token_SetHandleDacl` ignored the `NTSTATUS` returned by
`RtlCreateSecurityDescriptor` and `RtlSetDaclSecurityDescriptor`. If either
operation failed, the helper could still call `ZwSetSecurityObject` with a
descriptor whose DACL state was not proven. That can turn a local construction
failure into a later object-security mutation failure, and it hides the actual
failing API from the caller's existing status chain.

The official DACL setter also permits a NULL DACL, which grants unrestricted
access. This helper's local route is not a NULL-DACL policy route; it is a
restricted-token repair route that applies the already rebuilt ACL from
`Token_FilterDacl`. Therefore a NULL ACL is rejected locally before descriptor
construction.

## Official Shape

Microsoft documents these Windows driver API properties:

- `RtlCreateSecurityDescriptor` initializes an absolute-format security
  descriptor and returns `STATUS_SUCCESS` or `STATUS_UNKNOWN_REVISION`.
- `RtlSetDaclSecurityDescriptor` sets or supersedes DACL information on an
  absolute-format security descriptor and returns `NTSTATUS`.
- When `DaclPresent` is TRUE, `RtlSetDaclSecurityDescriptor` references the
  caller-supplied ACL rather than copying it.
- A NULL DACL grants unrestricted access and is not the same as an empty DACL.
- `ZwSetSecurityObject` sets object security state; `DACL_SECURITY_INFORMATION`
  requires `WRITE_DAC`, and the routine returns status such as invalid ACL,
  invalid handle, invalid SID, invalid security descriptor, or access denied.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlcreatesecuritydescriptor
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlsetdaclsecuritydescriptor
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwsetsecurityobject

## Fix

`Token_SetHandleDacl` now rejects a NULL ACL with `STATUS_INVALID_ACL`, stores
the construction status, checks `RtlCreateSecurityDescriptor`, checks
`RtlSetDaclSecurityDescriptor`, and only then calls `ZwSetSecurityObject`.

No token-filtering policy, SID selection, default-DACL buffer shape, target
object list, handle acquisition, or access mask changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-183.py
bash docs/plan/check-srev-183.sh
```

Runtime gate still required:

- Windows driver build proving `token.c` still compiles.
- Restricted-token launch smoke covering `Token_FilterDacl`.
- Verifier or failure-injection proof that `RtlCreateSecurityDescriptor` and
  `RtlSetDaclSecurityDescriptor` failures return before `ZwSetSecurityObject`.
- Object-open smoke proving the token, process, and thread DACL repairs still
  grant the intended user access after admin-group filtering.
