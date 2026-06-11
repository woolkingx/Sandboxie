# SREV-116 Advapi Header Out-Param Schema

## Data

Owner file:

```text
Sandboxie/core/dll/advapi.h
```

Consumer files:

```text
Sandboxie/core/dll/advapi.c
Sandboxie/core/dll/cred.c
```

Reviewed nodes:

```text
P_GetSecurityInfo
AdvApi_GetSecurityInfo
Ntmarta_GetSecurityInfo
P_CredRead
P_CredEnumerate
P_LookupAccountName
__sys_GetSecurityInfo
__sys_Ntmarta_GetSecurityInfo
__sys_CredReadA/W
__sys_CredEnumerateA/W
```

## Schema

`ADVAPI_HEADER_OUT_PARAM_SCHEMA` defines these local contracts:

- `advapi.h` owns the hooked Advapi/Cred function pointer shapes shared by
  `advapi.c` and `cred.c`.
- Hook typedefs that model Windows APIs preserve pointer-depth for out
  parameters.
- `GetSecurityInfo` receives `PSID *`, `PSID *`, `PACL *`, `PACL *`, and
  `PSECURITY_DESCRIPTOR *` output slots.
- `CredRead` receives a credential output slot, not a credential value.
- `CredEnumerate` receives a credential-array output slot, not an opaque input
  pointer.
- Hook implementation prototypes in `advapi.c` match the hooked API pointer
  typedef.
- This SREV does not change hook selection, access masks, window-station
  fallback behavior, credential serialization, credential conversion, or PStore
  merge logic.

## Topology

```text
Windows Advapi/Cred API contract
  -> advapi.h function pointer typedef
      -> __sys_* resolved function pointer
      -> SBIEDLL_HOOK replacement signature
          -> advapi.c / cred.c wrapper
          -> original API call with the same out-param pointer-depth
```

## Logic Risk

The old header compressed several out-parameter shapes into plain pointers:

- `P_GetSecurityInfo` used `PSID` and `PACL` where the API requires output slots
  (`PSID *` and `PACL *`).
- `P_CredRead` used `void *` where the API returns a credential pointer through
  an output slot.
- `P_CredEnumerate` used `void *` where the API returns an array of credential
  pointers through an output slot.

The calling ABI may survive this on common Windows targets because these values
are pointer-sized, but the schema is still wrong: ownership and writeback edges
are hidden from the compiler and from later review. Hook wrappers should model
the same data shape as the API they replace.

The duplicate `P_LookupAccountName` typedef had the same shape twice. It was not
a runtime behavior bug, but it made the header's API map less trustworthy during
schema review.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreadw
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credenumeratew
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountnamew

## Fix

`advapi.h` now preserves the official pointer-depth for `P_GetSecurityInfo`,
`P_CredRead`, and `P_CredEnumerate`, and keeps only one
`P_LookupAccountName` typedef. `advapi.c` hook prototypes and forwarding calls
now use `ppsidOwner`, `ppsidGroup`, `ppDacl`, and `ppSacl` to match the official
`GetSecurityInfo` shape.

No hook selection, `SetSecurityInfo` behavior, window-station fallback decision,
credential serialization, ANSI/Wide conversion, PStore merge, access mask, or
runtime policy was changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-116.py
bash docs/plan/check-srev-116.sh
```

Runtime/build gate still required:

- Windows x86/x64 build proving the typed hooks match the real imported API
  prototypes under the project's compiler settings.
- Runtime smoke for `GetSecurityInfo` / `ntmarta!GetSecurityInfo` DACL fallback
  on dummy window station.
- Sandboxed `CredReadA/W` and `CredEnumerateA/W` with native and PStore-backed
  credentials, proving returned blocks remain freed by the expected CredFree or
  local-free path.
