---
kind: srev-ledger-entry
id: SREV-008
title: Token Default DACL Mutation Manually Pre-Bumps ACL Size
status: patched-source-level-after-official-acl-api-shape-needs-windows-token-launch-run
owner: "Sandboxie/core/svc/ProcessServer.cpp:1154-1161"
spec: docs/plan/srev-008-token-default-dacl-spec.md
schema: docs/plan/srev-008-token-default-dacl-spec.schema.json
checker: docs/plan/check-srev-008.sh
runtime_gate: service/MSI custom-action launch still gives the intended caller access
---
### SREV-008: Token Default DACL Mutation Manually Pre-Bumps ACL Size

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ACL API shape; needs Windows token-launch runtime proof |
| Evidence | Explorer Newton reports `Sandboxie/core/svc/ProcessServer.cpp:1154-1161` manually increases `pAcl->AclSize` before `AddAccessAllowedAce`, ignores the return value, then writes the modified default DACL back with `SetTokenInformation`. |
| Data | `TOKEN_DEFAULT_DACL` and ACL buffer in an 8192-byte workspace. |
| Schema | ACL APIs own ACE insertion and capacity checks; `AddAccessAllowedAce` can fail with `ERROR_ALLOTTED_SPACE_EXCEEDED`. |
| Topology | SbieSvc modifies token default DACL for sandboxed service/RPCSS process creation. |
| Logic Risk | Manual size mutation can hide capacity failure or create an inconsistent ACL before it is placed on a token. |
| Official Shape | `docs/plan/srev-008-token-default-dacl-spec.md` records Microsoft `TOKEN_DEFAULT_DACL`, `GetTokenInformation`, opaque `ACL`, `GetAclInformation`, `ACL_SIZE_INFORMATION`, `AddAccessAllowedAce`, and `InitializeAcl` shape. |
| Fix | `RunSandboxedSetDacl` now rejects `DefaultDacl == NULL`, queries ACL size and revision with `GetAclInformation`, initializes an independent ACL buffer, copies existing ACEs with checked `GetAce` / `AddAce`, adds the caller ACE with checked `AddAccessAllowedAce`, and only then sets the token default DACL to the rebuilt ACL. |
| Acceptance Gate | `docs/plan/check-srev-008.sh` proves no direct `AclSize` mutation remains and all ACL API steps are checked before `SetTokenInformation`. Windows gate: service/MSI custom-action launch still gives the intended caller access. |
