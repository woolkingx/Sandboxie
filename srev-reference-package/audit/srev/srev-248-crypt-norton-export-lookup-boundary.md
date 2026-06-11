# SREV-248: Crypt Norton Export Lookup Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/crypt.c`, `Sandboxie/core/dll/sbiedll.h`, SREV-029, Microsoft `GetProcAddress` and CryptoAPI references |
| Output artifact | `docs/plan/srev-248-crypt-norton-export-lookup-boundary.schema.json`, `docs/plan/check-srev-248.py`, `docs/plan/check-srev-248.sh`, ledger fragment, comment-only source clarification |
| Owner | `Crypt_Init` hook installation policy for Crypt32 exports |
| Acceptance gate | targeted source checker plus core coverage/diff checkpoint; Windows Norton/Firefox compatibility proof remains required |

## Evidence

`Crypt_Init` resolves three Crypt32 exports and then installs hooks with the
shared `SBIEDLL_HOOK` macro:

```text
CryptProtectData
CryptUnprotectData
CertGetCertificateChain
```

`SBIEDLL_HOOK` writes the returned trampoline into `__sys_*` and returns
`FALSE` from the init function if the hook result is null. Therefore one
missing or unhookable export makes the whole `Crypt_Init` fail.

The local source has a Windows 8 / Norton 360 / Firefox branch. Before this
SREV it was labeled only as `$Workaround$ - 3rd party fix`, which hid the
owner decision. The actual topology is:

```text
GetProcAddress(CryptProtectData) fails
  -> Norton UMEngx86.dll is loaded on Windows 8+
  -> skip Crypt32 hook installation for this process
  -> return TRUE so module init continues
```

SREV-029 already owns the DPAPI broker wire schema when the hooks are installed.
This SREV does not change DPAPI request/reply packing.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
- https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/nf-wincrypt-certgetcertificatechain

## Data

`Crypt_Init`, `GetProcAddress`, `CryptProtectData`, `CryptUnprotectData`,
`CertGetCertificateChain`, `SBIEDLL_HOOK`, `__sys_CryptProtectData`,
`__sys_CryptUnprotectData`, `__sys_CertGetCertificateChain`, `Dll_OsBuild`,
`UMEngx86.dll`, Norton 360 toolbar compatibility, and SREV-029 DPAPI broker
wire schema.

## Schema

`CRYPT_NORTON_EXPORT_LOOKUP_BOUNDARY` says:

- Microsoft `GetProcAddress` returns NULL when an export address cannot be
  resolved.
- `SBIEDLL_HOOK` treats a null hook result as module-init failure.
- `Crypt_Init` owns the decision to install the complete Crypt32 hook surface or
  skip it for a known third-party export-lookup incompatibility.
- The Norton branch is not a DPAPI wire-schema fix and must not be used as a
  general permission to skip arbitrary Crypt32 failures.
- The branch is gated by missing `CryptProtectData`, Windows 8+ build, and
  loaded `UMEngx86.dll`.
- This SREV does not change Crypt32 hook behavior, DPAPI broker routing,
  certificate-chain behavior, or Norton compatibility behavior.

## Topology

Normal hook path:

```text
Crypt_Init
  -> GetProcAddress for CryptProtectData / CryptUnprotectData / CertGetCertificateChain
  -> SBIEDLL_HOOK for each export
  -> DPAPI calls may route through SREV-029 broker path
  -> CertGetCertificateChain may pre-start CryptSvc
```

Norton compatibility path:

```text
CryptProtectData export lookup is NULL
  -> Windows 8+ and UMEngx86.dll loaded
  -> do not install partial Crypt32 hook surface
  -> return TRUE from Crypt_Init
```

## Logic Risk

The old `$Workaround$` label made the branch look like unexplained residue. The
real boundary is hook-surface consistency: because `SBIEDLL_HOOK` returns
`FALSE` on a null hook, blindly continuing after a third-party export lookup
failure would fail module initialization. Trying to partially install only the
exports that were found would be a behavior change that splits the Crypt32 hook
surface and needs runtime proof.

The legal improvement here is to make the policy explicit without changing the
compatibility behavior.

## Fix

Comment-only source clarification. The old `$Workaround$` label now states that
the Norton 360 toolbar can make the `CryptProtectData` export lookup fail on
Windows 8, and that Sandboxie treats that as a module-owned hook surface
incompatibility: skip Crypt32 hooks for that process instead of failing
`Crypt_Init`.

## Acceptance Gate

`docs/plan/check-srev-248.py` validates the draft-07 schema, official reference
links, `GetProcAddress` lookup shape, `SBIEDLL_HOOK` failure topology, SREV-029
adjacency, the Norton compatibility branch, removal of the stale `$Workaround$`
label from `crypt.c`, and the ledger fragment.

Runtime gate: Windows 8+ Firefox/Norton 360 toolbar compatibility proof where
`UMEngx86.dll` is loaded and `CryptProtectData` lookup fails, plus normal
Crypt32 hook smoke proving DPAPI broker and `CertGetCertificateChain` behavior
are unchanged when exports resolve normally.
