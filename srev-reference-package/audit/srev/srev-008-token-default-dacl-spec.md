# SREV-008 Token Default DACL Mutation Shape

Status: source-level spec before patch.

## Official Shape

`TOKEN_DEFAULT_DACL.DefaultDacl` is the default ACL assigned to objects created
by the token user. `GetTokenInformation(TokenDefaultDacl)` retrieves this
structure, and `SetTokenInformation(TokenDefaultDacl)` sets it.

`GetTokenInformation` explicitly permits a token with no default DACL: in that
case `DefaultDacl` is `NULL`.

Microsoft documents `ACL` as opaque to applications. Applications should use ACL
functions to create and manipulate ACLs rather than editing ACL members
directly. `GetAclInformation(AclSizeInformation)` returns `AceCount`,
`AclBytesInUse`, and `AclBytesFree`. `AddAccessAllowedAce` returns failure when
the ACE cannot fit, including `ERROR_ALLOTTED_SPACE_EXCEEDED`.

For a newly allocated ACL buffer, `InitializeAcl` requires a DWORD-aligned length
large enough for the ACL header and ACEs.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_default_dacl
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-acl
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getaclinformation
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-acl_size_information
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-addaccessallowedace
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-initializeacl

## Local Shape

`ProcessServer::RunSandboxedSetDacl` adjusts a duplicated token before launching
a sandboxed service or helper process. It adds the caller user SID or logon SID
to the new token's default DACL so the caller can open descendant processes.

## Local Risk

The previous implementation manually increased `pAcl->AclSize`, ignored
`AddAccessAllowedAce` failure, then wrote the DACL back to the token. It also
assumed `DefaultDacl` was non-NULL.

That violates the official ACL ownership model and can hide capacity or shape
failures before `SetTokenInformation`.

## Patch Boundary

Do not change caller SID selection or access-mask policy.

Build a new ACL in an independent buffer:

1. Reject `DefaultDacl == NULL` until a project policy chooses a replacement
   empty/default DACL shape.
2. Query the existing ACL size with `GetAclInformation`.
3. Allocate and initialize a new ACL buffer so the old ACL remains readable
   while ACEs are copied.
4. Copy existing ACEs with `GetAce` / `AddAce`.
5. Add the caller ACE with `AddAccessAllowedAce` and check its return value.
6. Set the token default DACL only after the new ACL is fully valid.

## Acceptance Gate

- No code writes `pAcl->AclSize`.
- `DefaultDacl == NULL` is gated before ACL API calls.
- `GetAclInformation(AclSizeInformation)` succeeds before ACL sizing.
- `GetAclInformation(AclRevisionInformation)` supplies the ACL revision used for
  the rebuilt ACL.
- `InitializeAcl`, `GetAce` / `AddAce`, and `AddAccessAllowedAce` return values
  are checked.
- `SetTokenInformation(TokenDefaultDacl)` receives the rebuilt ACL only after the
  new ACE is added successfully.
- Runtime gate remains open: MSI/service custom-action launch still grants the
  intended caller access on Windows.
