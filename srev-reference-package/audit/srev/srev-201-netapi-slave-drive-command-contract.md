# SREV-201: NetApi Slave Drive Command Contract

Stage: schema -> boundary -> action -> verify

Input artifact: `Sandboxie/core/svc/netapiserver.h` and
`Sandboxie/core/svc/netapiserver.cpp`

Output artifact: the NetAPI slave command parser validates the drive-letter
command shape before calling `DefineDosDevice`.

Owner: `Sandboxie/core/svc/netapiserver.h` /
`Sandboxie/core/svc/netapiserver.cpp`

Acceptance gate: `docs/plan/check-srev-201.py` plus
`docs/plan/check-srev-201.sh`.

## Data

`NetApiServer::UseAdd` brokers selected `NetUseAdd` calls. On successful drive
mapping it launches a same-user helper process with a command shape like:

```text
Sandboxie_NetProxy:Use=Z
```

The helper path is:

```text
LaunchSlave
  -> SbieDll_RunFromHome(SbieSvc.exe, "Sandboxie_NetProxy:Use=<drive>")
  -> CreateProcessAsUser
  -> WinMain detects Sandboxie_NetProxy
  -> NetApiServer::RunSlave
  -> DefineDosDevice(DDD_LUID_BROADCAST_DRIVE, "<drive>:", NULL)
```

Local evidence before this entry:

- `LaunchSlave` accepted any two-character `local` string ending in `:`, even
  when the first character was not a drive letter.
- `RunSlave` matched `:Use=` and passed `towupper(cmdline[5])` into
  `DefineDosDevice` as `<char>:` without checking that the character was a
  drive letter.
- `RunSlave` did not verify that the command ended after the drive character or
  at a command-line delimiter, so malformed suffixes still selected the first
  character.

## Official API Shape

`NetUseAdd` can establish a connection with a local drive letter or printer
device:

https://learn.microsoft.com/en-us/windows/win32/api/lmuse/nf-lmuse-netuseadd

`USE_INFO_2.ui2_local` is the local device name, such as a drive or printer
device:

https://learn.microsoft.com/en-us/windows/win32/api/lmuse/ns-lmuse-use_info_2

`DefineDosDeviceW` defines, redefines, or deletes MS-DOS device names. Microsoft
documents that a drive letter device name is a string such as `C:` and that a
trailing backslash is not allowed:

https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-definedosdevicew

`CreateProcessAsUserW` creates the helper in the security context represented by
the primary token:

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw

## Boundary

The boundary is:

```text
NetUseAdd local device string
  -> service-side LaunchSlave command
  -> new helper process command line
  -> DefineDosDevice drive device name
```

`NetApiServer` owns converting a successful local drive mapping into the helper
command and then into a `DefineDosDevice` drive name. A malformed local device
or malformed slave command must not reach `DefineDosDevice`.

## Topology

```text
UseAdd success
  -> LaunchSlave(len, local)
     -> require len == 2
     -> require local[0] is A-Z or a-z
     -> require local[1] == ':'
     -> emit Sandboxie_NetProxy:Use=<drive>

RunSlave
  -> find ':Use='
  -> require drive is A-Z or a-z
  -> require command terminator after drive
  -> uppercase drive
  -> DefineDosDevice(DDD_LUID_BROADCAST_DRIVE, "X:", NULL)
```

## Logic

The helper command is a tiny protocol. Its legal data shape is exactly one drive
letter, not an arbitrary WCHAR before a colon. Because `DefineDosDevice` updates
the MS-DOS device namespace, the parser must reject malformed command data
before entering that API.

This SREV preserves:

- existing `NetUseAdd` validation and impersonation topology;
- success-only `LaunchSlave`;
- same-user `CreateProcessAsUser` helper launch;
- `DDD_LUID_BROADCAST_DRIVE` behavior for valid drive letters.

## Verification

Linux source gates prove:

- `LaunchSlave` and `RunSlave` both use a shared drive-letter predicate;
- `RunSlave` checks for `:Use=`, a valid drive letter, and a command terminator
  before `DefineDosDevice`;
- `DefineDosDevice` receives the normalized uppercase drive letter;
- SREV-129 `NetUseAdd` wire validation remains intact.

Runtime gate:

- Windows service build.
- Valid mapped-drive smoke still broadcasts the drive change.
- Malformed helper command lines such as `Sandboxie_NetProxy:Use=\`,
  `Sandboxie_NetProxy:Use=1`, and `Sandboxie_NetProxy:Use=Z:extra` do not call
  `DefineDosDevice`.
