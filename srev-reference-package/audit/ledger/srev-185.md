---
kind: srev-ledger-entry
id: SREV-185
title: DLL LSA Untrusted Fallback Contract
status: patched-source-level-after-official-lsa-api-shape-review-needs-windows-dll-runtime-proof
owner: Sandboxie/core/dll/lsa.c
spec: docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.md
schema: docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.schema.json
checker: docs/plan/check-srev-185.py
runtime_gate: Windows DLL build for Secur32 and SspiCli targets, fallback smoke from trusted registration failure to LsaConnectUntrusted, and KPATH-004/KPATH-006 regression smoke
---
### SREV-185: DLL LSA Untrusted Fallback Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official LSA API shape review; needs Windows DLL runtime proof |
| Evidence | `Sandboxie/core/dll/lsa.c` was the highest-ranked unnamed reviewable core file after SREV-184. It owns the DLL-side hook for `LsaRegisterLogonProcess`: the hook first calls the real trusted registration API and, if that fails, falls back to `LsaConnectUntrusted`. Microsoft documents both APIs as returning `NTSTATUS`, but the old `P_LsaConnectUntrusted` typedef returned `ULONG` while the call result was assigned to an `NTSTATUS` variable. The fallback pointer was resolved before hook install but not gated, so a hooked trusted-registration failure could call a missing fallback pointer. |
| Data | `Sandboxie/core/dll/lsa.c`, `Sandboxie/core/dll/ldr.c`, `Sandboxie/core/dll/sbiedll.h`, `Lsa_Init_Common`, `Lsa_Init_Secur32`, `Lsa_Init_SspiCli`, `Lsa_LsaRegisterLogonProcess`, `P_LsaConnectUntrusted`, `P_LsaRegisterLogonProcess`, `__sys_LsaConnectUntrusted`, `__sys_LsaRegisterLogonProcess`, `SBIEDLL_HOOK`, `Secur32.dll`, `SspiCli.dll`, KPATH-004, and KPATH-006. |
| Schema | `DLL_LSA_UNTRUSTED_FALLBACK_CONTRACT` says `lsa.c` owns DLL-side interception of `LsaRegisterLogonProcess`; `LsaRegisterLogonProcess` returns `NTSTATUS` and local failure falls back to `LsaConnectUntrusted`; `LsaConnectUntrusted` returns `NTSTATUS`, not `ULONG`; the fallback target must be resolved before installing the `LsaRegisterLogonProcess` hook; `SBIEDLL_HOOK` owns detour install and original-function writeback for `__sys_LsaRegisterLogonProcess`; Secur32 is used before Windows 7 and SspiCli on Windows 7+ according to existing local dispatch; LSA endpoint policy, KPATH-004 LSAD semantics, KPATH-006 RPC parsing, `OpenLsaEndpoint`, and trusted-to-untrusted fallback decision must not change. |
| Topology | Loader dispatch routes `secur32.dll` to `Lsa_Init_Secur32` and `sspicli.dll` to `Lsa_Init_SspiCli`. `Lsa_Init_Common` resolves `LsaConnectUntrusted`, resolves and hooks `LsaRegisterLogonProcess`, and the hook later runs `__sys_LsaRegisterLogonProcess` followed by `__sys_LsaConnectUntrusted` only on failure. Driver-side LSARPC endpoint filtering remains owned by `Sandboxie/core/drv/ipc_lsa.c` and tracked by KPATH-004/KPATH-006. |
| Logic Risk | Return-type drift at an API boundary makes status handling look like a generic integer rather than the official LSA/NT status contract. The missing fallback pointer gate also hid the real dependency of the hook: once trusted registration is intercepted, untrusted connection must be callable before the hook can safely fall back. |
| Official Shape | `docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.md` records Microsoft `LsaConnectUntrusted` and `LsaRegisterLogonProcess` references. `docs/plan/srev-185-dll-lsa-untrusted-fallback-contract.schema.json` records the JSON Schema draft-07 local `DLL_LSA_UNTRUSTED_FALLBACK_CONTRACT` contract. |
| Fix | `P_LsaConnectUntrusted` now returns `NTSTATUS`. `Lsa_Init_Common` now returns `FALSE` before installing the `LsaRegisterLogonProcess` hook if `LsaConnectUntrusted` cannot be resolved. No LSA endpoint policy, RPC/LSAD opnum handling, module dispatch decision, trusted-registration fallback decision, or handle ownership behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-185.py` validates the draft-07 schema, official references, DLL LSA typedef shape, fallback pointer gate before hook install, trusted-to-untrusted fallback flow, loader dispatch, `SBIEDLL_HOOK` ownership, and ledger fragment; `docs/plan/check-srev-185.sh` is the matrix wrapper. Runtime gate: Windows DLL build for Secur32 and SspiCli targets, sandboxed trusted-registration failure falling back to `LsaConnectUntrusted`, and KPATH-004/KPATH-006 driver-side LSARPC policy regression smoke. |
