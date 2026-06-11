---
kind: srev-ledger-entry
id: SREV-248
title: Crypt Norton Export Lookup Boundary
status: patched-comment-topology-after-official-getprocaddress-and-cryptoapi-review-no-behavior-change
owner: Sandboxie/core/dll/crypt.c
spec: docs/plan/srev-248-crypt-norton-export-lookup-boundary.md
schema: docs/plan/srev-248-crypt-norton-export-lookup-boundary.schema.json
checker: docs/plan/check-srev-248.py
runtime_gate: Windows 8+ Firefox/Norton 360 toolbar compatibility proof plus normal Crypt32 hook smoke
---

### SREV-248: Crypt Norton Export Lookup Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `GetProcAddress` and CryptoAPI review; no behavior change |
| Evidence | `Crypt_Init` resolves `CryptProtectData`, `CryptUnprotectData`, and `CertGetCertificateChain`, then installs hooks through `SBIEDLL_HOOK`. The shared macro returns `FALSE` from the init function when a hook result is null. The Norton 360 / Firefox branch was labeled only as `$Workaround$ - 3rd party fix`; the actual local decision is to return `TRUE` and skip the Crypt32 hook surface when `CryptProtectData` lookup fails on Windows 8+ with `UMEngx86.dll` loaded. |
| Data | `Crypt_Init`, `GetProcAddress`, `CryptProtectData`, `CryptUnprotectData`, `CertGetCertificateChain`, `SBIEDLL_HOOK`, `__sys_CryptProtectData`, `__sys_CryptUnprotectData`, `__sys_CertGetCertificateChain`, `Dll_OsBuild`, `UMEngx86.dll`, Norton 360 toolbar compatibility, and SREV-029 DPAPI broker wire schema. |
| Schema | `CRYPT_NORTON_EXPORT_LOOKUP_BOUNDARY` says Microsoft `GetProcAddress` returns NULL when an export address cannot be resolved; `SBIEDLL_HOOK` treats a null hook result as module-init failure; `Crypt_Init` owns the decision to install the complete Crypt32 hook surface or skip it for a known third-party export-lookup incompatibility; the Norton branch is not a DPAPI wire-schema fix and must not be used as a general permission to skip arbitrary Crypt32 failures; the branch is gated by missing `CryptProtectData`, Windows 8+ build, and loaded `UMEngx86.dll`; this SREV does not change Crypt32 hook behavior, DPAPI broker routing, certificate-chain behavior, or Norton compatibility behavior. |
| Topology | Normal path is `Crypt_Init`, `GetProcAddress` for the three Crypt32 exports, `SBIEDLL_HOOK` for each export, then DPAPI may route through the SREV-029 broker path and `CertGetCertificateChain` may pre-start CryptSvc. Norton compatibility path is failed `CryptProtectData` export lookup, Windows 8+ and `UMEngx86.dll` loaded, no partial Crypt32 hook surface installed, and `Crypt_Init` returns `TRUE`. |
| Logic Risk | The old `$Workaround$` label hid the hook-surface consistency decision. Because `SBIEDLL_HOOK` returns `FALSE` on a null hook, blindly continuing after a third-party export lookup failure would fail module initialization. Partially installing only the exports that were found would split the Crypt32 hook surface and needs runtime proof. |
| Official Shape | `docs/plan/srev-248-crypt-norton-export-lookup-boundary.md` records Microsoft `GetProcAddress`, `CryptProtectData`, `CryptUnprotectData`, and `CertGetCertificateChain` references. `docs/plan/srev-248-crypt-norton-export-lookup-boundary.schema.json` records the JSON Schema draft-07 local `CRYPT_NORTON_EXPORT_LOOKUP_BOUNDARY` contract. |
| Fix | Comment-only source clarification. The old `$Workaround$` label now states that the Norton 360 toolbar can make the `CryptProtectData` export lookup fail on Windows 8, and that Sandboxie treats that as a module-owned hook surface incompatibility: skip Crypt32 hooks for that process instead of failing `Crypt_Init`. |
| Acceptance Gate | `docs/plan/check-srev-248.py` validates the draft-07 schema, official reference links, `GetProcAddress` lookup shape, `SBIEDLL_HOOK` failure topology, SREV-029 adjacency, the Norton compatibility branch, removal of the stale `$Workaround$` label from `crypt.c`, and the ledger fragment. Runtime gate: Windows 8+ Firefox/Norton 360 toolbar compatibility proof where `UMEngx86.dll` is loaded and `CryptProtectData` lookup fails, plus normal Crypt32 hook smoke proving DPAPI broker and `CertGetCertificateChain` behavior are unchanged when exports resolve normally. |
