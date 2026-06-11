# SREV-321: Proc MSI Systemless Process Gate

## Data

`Sandboxie/core/dll/proc.c` owns the DLL-side `Proc_CreateProcessInternalW`
detour. In compartment mode or `OriginalToken` mode, the normal token-changing
path is bypassed and the code calls `__sys_CreateProcessInternalW` directly.
Inside that direct-create branch, a narrow MSI predicate clears `hToken` and
`lpProcessAttributes` when Sandboxie's MSIServer is running systemless.

The relevant data nodes are:

```text
Proc_CreateProcessInternalW
Dll_CompartmentMode / OriginalToken
DLL_IMAGE_MSI_INSTALLER
Scm_MsiServer_Systemless
RunServicesAsSystem
MsiInstallerExemptions
hToken
lpProcessAttributes
__sys_CreateProcessInternalW
Scm_SetupMsiHooks
```

## Official Shape

Microsoft documents `CreateProcessW` as creating a process and primary thread in
the calling process security context. `lpProcessAttributes` may supply a process
security descriptor and handle inheritance shape; when it or its security
descriptor is `NULL`, the new process receives the default descriptor.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
```

Microsoft documents `CreateProcessAsUserW` as the explicit-token process
creation API that runs the new process in the security context represented by a
primary token.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw
```

Microsoft documents access tokens as the objects that describe the security
context of a process or thread.

```text
https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens
```

Microsoft's Windows Installer `ServiceInstall` table documents service
configuration and notes that `CreateService` uses the LocalSystem account when
the service account name is null.

```text
https://learn.microsoft.com/en-us/windows/win32/msi/serviceinstall-table
```

`CreateProcessInternalW` is not the public Microsoft API contract. This SREV
therefore records only the local Sandboxie owner split: the MSI systemless hook
state comes from `scm_msi.c`; this `proc.c` branch owns the direct-create
token/security-attributes gate.

## Schema

Local schema:

```text
docs/plan/srev-321-proc-msi-systemless-process-gate.schema.json
```

`PROC_MSI_SYSTEMLESS_PROCESS_GATE` says:

- MSI systemless state is owned by `scm_msi.c`;
- process creation token/security-attributes selection is owned by this
  `proc.c` branch;
- the branch is legal only for `DLL_IMAGE_MSI_INSTALLER`,
  `Scm_MsiServer_Systemless`, not `RunServicesAsSystem`, and not
  `MsiInstallerExemptions`;
- clearing `hToken` and `lpProcessAttributes` must stay local to that exact
  predicate;
- SREV-092 owns MSI in-use event lifetime; SREV-270 owns the Config.Msi file
  retry; this SREV does not modify either;
- this SREV changes comments and proof only, not process creation behavior.

## Topology

```text
MSI process creation request
  -> Proc_CreateProcessInternalW direct-create branch
  -> systemless MSI predicate
  -> hToken/lpProcessAttributes preserved or cleared
  -> __sys_CreateProcessInternalW
```

Adjacent MSI topology remains separate:

```text
scm_msi.c -> Scm_SetupMsiHooks -> Scm_MsiServer_Systemless
scm_msi.c -> Scm_MsiDll -> MSI in-use event lifetime (SREV-092)
file.c -> Config.Msi directory retry (SREV-270)
```

## Logic Risk

The old comment said this was a simple MSI workaround. That hides the security
boundary: the branch changes the process creation token and process-security
attributes for a very narrow systemless MSI server condition. Future edits
should not broaden or remove the predicate without Windows MSI runtime proof.

## Fix

Comment-only source clarification. The source now names the branch as the
SREV-321 systemless MSI server child process creation gate and records that the
existing predicate is the only scope for clearing `hToken` and
`lpProcessAttributes`.

No token value, process-attributes value, predicate, direct-create call, MSI
hook state, in-use event, or Config.Msi file behavior changed.

## Acceptance Gate

`docs/plan/check-srev-321.py` validates the draft-07 schema, official Microsoft
references, the source comment, preservation of the MSI systemless predicate,
preservation of the `hToken` and `lpProcessAttributes` assignments, stale
workaround wording removal from this branch, SREV-092/SREV-270 adjacency, and
the split ledger fragment.

Windows gate: MSI install/repair/custom-action smoke with systemless MSIServer,
`RunServicesAsSystem` negative smoke, `MsiInstallerExemptions` negative smoke,
and regression checks for SREV-092 MSI lifetime plus SREV-270 Config.Msi retry.
