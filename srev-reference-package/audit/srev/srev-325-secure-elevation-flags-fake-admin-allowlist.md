# SREV-325: Secure Elevation Flags Fake Admin Allowlist

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/secure.c`, SREV-307, Microsoft UAC and token elevation references |
| Output artifact | `docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.schema.json`, `docs/plan/check-srev-325.py`, `docs/plan/check-srev-325.sh`, ledger fragment, comment-only source clarification |
| Owner | `Secure_Init` allowlist for `Secure_RtlQueryElevationFlags` zero-flag faking |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`Secure_Init` resolves `RtlQueryElevationFlags`, installs
`Secure_RtlQueryElevationFlags`, then sets `Secure_ShouldFakeRunningAsAdmin` for
this local allowlist:

```text
Sandboxie SbieSvc
Sandboxie RpcSs
Internet Explorer
SynTPEnh.exe
SynTPHelper.exe
```

`Secure_RtlQueryElevationFlags` is the transition owner. It may return zero
flags instead of calling the native function when one of these local conditions
is true:

- `Secure_FakeAdmin`;
- `TlsData->proc_create_process_fake_admin`;
- Internet Explorer outside `proc_create_process`;
- SbieSvc during `proc_create_process`;
- Sandboxie RpcSs or Synaptics callers.

Internet Explorer has additional adjacency:

- IE tab processes are detected by command-line markers `SCODEF:` and `CREDAT:`.
- IE Protected Mode registry fakes are owned by SREV-307 in
  `Key_NtQueryValueKeyFakeForInternetExplorer`.

## Official Shape

Microsoft documents UAC as limiting administrator privileges and describes the
standard-user token versus full administrator token split.

```text
https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/how-it-works
```

Microsoft's UAC architecture describes `CreateProcess` returning
`ERROR_ELEVATION_REQUIRED`, `ShellExecute` handling that error, and installer
detection / requested execution level as the official elevation path.

```text
https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/architecture
```

Microsoft documents `TOKEN_INFORMATION_CLASS` as the public token information
selector used by `GetTokenInformation`, including `TokenElevationType` and
`TokenElevation`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class
```

Microsoft documents `TOKEN_ELEVATION_TYPE` as the public enum for default,
full, or limited token elevation type.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_elevation_type
```

No public Microsoft Win32 API page was found for `RtlQueryElevationFlags` during
this pass. This SREV therefore treats that routine as a local observed ntdll
hook target, not as an official public API schema.

## Schema

Local schema:

```text
docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.schema.json
```

`SECURE_ELEVATION_FLAGS_FAKE_ADMIN_ALLOWLIST` says:

- official UAC/token documentation owns elevation semantics;
- `RtlQueryElevationFlags` is a local observed ntdll hook target, not a public
  Microsoft Win32 schema in this SREV;
- `Secure_Init` owns only the process/image allowlist for the hook;
- `Secure_RtlQueryElevationFlags` owns the local decision to return zero flags
  or forward to native;
- IE Protected Mode registry fake values remain owned by SREV-307 / `key.c`;
- this SREV changes comments and proof only.

## Topology

```text
Secure_Init
  -> resolve RtlQueryElevationFlags
  -> install Secure_RtlQueryElevationFlags hook
  -> set Secure_ShouldFakeRunningAsAdmin allowlist
```

```text
caller queries elevation flags
  -> Secure_RtlQueryElevationFlags
  -> Secure_FakeAdmin / proc_create_process_fake_admin / allowlist sub-gate
  -> zero Flags + STATUS_SUCCESS
  -> otherwise __sys_RtlQueryElevationFlags
```

IE adjacency:

```text
IE command line markers -> Secure_IsInternetExplorerTabProcess
  -> Secure_RtlQueryElevationFlags IE gate
  -> separate SREV-307 key.c Protected Mode fake-value owner
```

## Logic Risk

The old `$Workaround$ - 3rd party fix` label hid the actual local contract:
this is not a broad third-party bypass. It is an allowlist for one hook's
zero-flag faking behavior. Future changes must not add images to this list
without naming whether the caller is an IE Protected Mode path, SbieSvc UAC
elevator path, RpcSs broker path, or another caller with a Windows runtime
compatibility gate.

## Fix

Comment-only source clarification. The source now names SREV-325 and says the
allowlist feeds `RtlQueryElevationFlags` zero-flag faking for IE,
SbieSvc/RpcSs brokers, and Synaptics callers.

No hook installation, image predicate, `Secure_ShouldFakeRunningAsAdmin`
assignment, `Secure_RtlQueryElevationFlags` branch, returned flag value, status,
or native forwarding behavior changed.

## Acceptance Gate

`docs/plan/check-srev-325.py` validates the draft-07 schema, official Microsoft
references, source comment, preserved allowlist, preserved IE sub-gates,
preserved SbieSvc create-process gate, preserved generic broker/Synaptics fake
path, native forwarding fallback, SREV-307 adjacency, stale workaround wording
removal, and split ledger fragment.

Windows gate: IE Protected Mode / ActiveX install broker smoke, SbieSvc UAC
elevator smoke, SandboxieRpcSs elevated COM smoke, Synaptics compatibility smoke
if available, and negative control proving non-allowlisted callers still forward
to native `RtlQueryElevationFlags`.
