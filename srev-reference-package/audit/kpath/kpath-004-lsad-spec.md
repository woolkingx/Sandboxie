# KPATH-004 LSAD Endpoint Shape

This note records the official API/protocol shape before changing Sandboxie's
LSA endpoint policy. The boundary is not just `\RPC Control\LSARPC_ENDPOINT`;
that endpoint carries MS-LSAD operations over local RPC.

## Official Shape

Microsoft's LSA policy model has four object families:

- `Policy`: global local-security policy.
- `TrustedDomain`: trust relationship information.
- `Account`: user, group, or local-group policy account information.
- `Private Data`: protected encrypted information, including service account
  passwords.

Official reference:

- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/lsa-policy-objects`

`LsaOpenPolicy` / `LsarOpenPolicy*` opens a policy object handle. The semantic
decision is not the open call alone; it is the requested `DesiredAccess` and the
later operation that consumes the returned context handle.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-lsaopenpolicy`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/9456a963-7c21-4710-af77-d0a2f5a72d6b`
- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/policy-object-access-rights`

The policy-object access mask has a sharp split:

- `POLICY_LOOKUP_NAMES` and `POLICY_VIEW_LOCAL_INFORMATION` support lookup/read
  style operations.
- `POLICY_CREATE_SECRET`, `POLICY_CREATE_ACCOUNT`, `POLICY_TRUST_ADMIN`,
  `POLICY_SET_AUDIT_REQUIREMENTS`, `POLICY_AUDIT_LOG_ADMIN`, and
  `POLICY_SERVER_ADMIN` are mutation or security-admin capabilities.
- `POLICY_GET_PRIVATE_INFORMATION` is sensitive read capability.

The secret/private-data object shape is explicit:

- `SECRET_SET_VALUE`: set secret value.
- `SECRET_QUERY_VALUE`: query secret value.
- Private Data objects store protected encrypted data such as service account
  passwords.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/private-data-object`
- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/private-data-object-access-rights`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/88c6bd18-6c40-4a82-ae19-fe7bfec5108b`

## Opnum Surface

MS-LSAD publishes a method table in RPC opnum order. For this audit, the critical
secret/private-data methods are:

| Opnum | Method | Semantic Class | Sandboxie Route |
|---|---|---|---|
| `0x10` | `LsarCreateSecret` | secret create | deny |
| `0x1C` | `LsarOpenSecret` | secret handle open | deny until DesiredAccess parser exists |
| `0x1D` | `LsarSetSecret` | secret write/delete | deny |
| `0x1E` | `LsarQuerySecret` | secret read | deny |
| `0x22` | `LsarDeleteObject` | delete account/secret/trust object | deny |
| `0x2A` | `LsarStorePrivateData` | private-data write | deny |
| `0x2B` | `LsarRetrievePrivateData` | private-data read | deny |
| `0x88` | `LsarOpenSecret2` | secret handle open | deny until DesiredAccess parser exists |
| `0x89` | `LsarCreateSecret2` | secret create | deny |
| `0x8A` | `LsarSetSecret2` | secret write/delete | deny |
| `0x8B` | `LsarQuerySecret2` | secret read | deny |
| `0x8C` | `LsarStorePrivateData2` | private-data write | deny |
| `0x8D` | `LsarRetrievePrivateData2` | private-data read | deny |

Official references:

- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/2c6f3cf9-d792-4e8b-9af5-5470f636c20a`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/c86d4a49-e9dd-43f8-8ab1-44f6baffa2a0`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/35a984a1-d002-4d60-946d-b557ff4c46e0`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/8bf25269-014f-43fd-b80f-7a59a4883451`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/21c1a153-032c-4869-afc9-186b2346dfab`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/e36cfffa-fd53-437e-a5a7-1a95cfdda4c1`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/8d0aa2dc-22b6-4bc3-b5d2-79b4b0ad7bce`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/b79c94fe-d717-4ecf-963c-a200682921dc`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/b46f3725-d3de-46b7-8245-a14edeb278a1`

## Local Evidence

- `Sandboxie/core/drv/ipc_lsa.c` filters `\RPC Control\LSARPC_ENDPOINT` by a
  message ID extracted from the local RPC payload.
- `Sandboxie/core/drv/ipc.c` includes `\RPC Control\LSARPC_ENDPOINT` in the
  default Windows 7 IPC open path list.
- `Sandboxie/install/SbieSettings.ini` exposes `OpenLsaEndpoint`, described as
  allowing access to Local Security Authority endpoints.
- `CHANGELOG.md` records the LSARPC endpoint filter as the fix for
  CVE-2019-13502 and says it prevented system options from being changed.

## Strategy Decision

The coarse opnum filter is legal only for operations whose method identity alone
is sensitive. Secret/private-data methods satisfy that rule because the official
API names them as secret read/write/create/open/delete operations.

`LsarOpenPolicy*` does not satisfy that rule. It can request benign lookup
access or admin/secret/trust access through `DesiredAccess`. The correct next
shape is a stub parser that extracts `DesiredAccess` for `LsarOpenPolicy`,
`LsarOpenPolicy2`, `LsarOpenPolicy3`, and `LsarOpenPolicyWithCreds`, after
KPATH-006 proves the local RPC payload layout.

Until that parser exists:

- deny known secret/private-data opnums early;
- keep existing lookup/query compatibility paths unchanged;
- do not claim Event ID 6033 is solved unless a Windows trace maps it to a
  specific opnum and process.
