# SREV-185 DLL LSA Untrusted Fallback Contract

## Data

Owner file:

```text
Sandboxie/core/dll/lsa.c
```

Reviewed nodes:

```text
Lsa_Init_Common
Lsa_Init_Secur32
Lsa_Init_SspiCli
Lsa_LsaRegisterLogonProcess
P_LsaConnectUntrusted
P_LsaRegisterLogonProcess
__sys_LsaConnectUntrusted
__sys_LsaRegisterLogonProcess
SBIEDLL_HOOK
```

## Schema

`DLL_LSA_UNTRUSTED_FALLBACK_CONTRACT` defines these local contracts:

- `lsa.c` owns DLL-side interception of `LsaRegisterLogonProcess`.
- `LsaRegisterLogonProcess` returns `NTSTATUS`; on failure the local hook falls back to `LsaConnectUntrusted`.
- `LsaConnectUntrusted` also returns `NTSTATUS`, not `ULONG`.
- The fallback target must be resolved before installing the `LsaRegisterLogonProcess` hook.
- `SBIEDLL_HOOK` remains the owner of the detour install and original-function writeback for `__sys_LsaRegisterLogonProcess`.
- `Secur32.dll` is used before Windows 7 and `SspiCli.dll` is used on Windows 7+ according to the existing local dispatch.
- This SREV does not change LSA endpoint policy, KPATH-004 LSAD semantics, KPATH-006 RPC parsing, `OpenLsaEndpoint`, or the trusted-to-untrusted fallback decision.
- Windows runtime proof is required.

## Topology

The DLL-side hook route is:

```text
Ldr module init
  -> Lsa_Init_Secur32 or Lsa_Init_SspiCli
  -> Lsa_Init_Common
  -> resolve LsaConnectUntrusted
  -> resolve and hook LsaRegisterLogonProcess
  -> Lsa_LsaRegisterLogonProcess
  -> __sys_LsaRegisterLogonProcess
  -> on failure, __sys_LsaConnectUntrusted
```

This is separate from the driver LSARPC endpoint policy owned by
`Sandboxie/core/drv/ipc_lsa.c` and tracked by KPATH-004/KPATH-006.

## Logic Risk

Before this SREV, `P_LsaConnectUntrusted` used `ULONG` even though the result is
immediately assigned into an `NTSTATUS` variable. The binary width is the same,
but the schema is wrong at the API boundary and hides that the fallback returns
LSA/NT status codes.

The fallback function pointer was also resolved before the hook, but it was not
gated. If `LsaRegisterLogonProcess` was successfully hooked and later failed,
the fallback call could dereference a missing `__sys_LsaConnectUntrusted`
pointer. The official API is available on the supported Windows line, so failing
initialization when the fallback is absent is the correct local boundary.

## Official Shape

Microsoft documents `LsaConnectUntrusted` as:

```text
NTSTATUS LsaConnectUntrusted(PHANDLE LsaHandle)
```

It returns `STATUS_SUCCESS` or another `NTSTATUS` code and returns an untrusted
LSA connection handle for future authentication-service calls.

Microsoft documents `LsaRegisterLogonProcess` as:

```text
NTSTATUS LsaRegisterLogonProcess(
  PLSA_STRING LogonProcessName,
  PHANDLE LsaHandle,
  PLSA_OPERATIONAL_MODE SecurityMode)
```

It verifies that the caller is a logon application; callers with `SeTcbPrivilege`
can create a trusted connection, while applications that only need authentication
package queries can use `LsaConnectUntrusted`.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-lsaconnectuntrusted
- https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-lsaregisterlogonprocess

## Fix

`P_LsaConnectUntrusted` now returns `NTSTATUS`. `Lsa_Init_Common` now fails
before installing the `LsaRegisterLogonProcess` hook if `LsaConnectUntrusted`
cannot be resolved.

No LSA endpoint policy, RPC/LSAD opnum handling, module dispatch decision,
trusted-registration fallback decision, or handle ownership behavior changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-185.py
bash docs/plan/check-srev-185.sh
```

Runtime gate still required:

- Windows DLL build for the Secur32 and SspiCli hook targets.
- Sandboxed caller that fails trusted `LsaRegisterLogonProcess` and succeeds via
  `LsaConnectUntrusted`.
- Regression smoke proving KPATH-004/KPATH-006 driver-side LSARPC policy is
  unchanged.
