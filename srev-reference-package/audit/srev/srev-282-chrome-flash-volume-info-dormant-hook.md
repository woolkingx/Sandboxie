# SREV-282: Chrome Flash Volume-Info Dormant Hook

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file_init.c`, `Sandboxie/core/dll/file_misc.c`, SREV-273, SREV-279, and Microsoft `GetVolumeInformationW` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | Dormant `GetVolumeInformationW` Chrome Flash compatibility hook stub |
| Acceptance gate | Targeted checker validates official references, dormant registration/body state, active volume-info owner adjacency, stale workaround wording removal, and ledger fragment |

## Data

Two inactive source blocks describe an old `GetVolumeInformationW` hook:

```text
file_init.c:
  commented GetProcAddress("GetVolumeInformationW")
  commented SBIEDLL_HOOK(File_,GetVolumeInformationW)

file_misc.c:
  commented File_GetVolumeInformationW body
  Chrome all-null output-parameter predicate
  commented TRUE return for that special case
  commented pass-through to __sys_GetVolumeInformationW
```

The current active volume-information owners are separate:

- `File_NtQueryVolumeInformationFile` owns the native volume-info hook surface,
  including SREV-279's named-pipe `FileFsDeviceInformation` fast path.
- `File_GetFinalPathNameByHandleW_2` / SREV-273 own caller-visible final-path
  volume-name presentation.
- `Kernel_GetVolumeInformationByHandleW` owns the active by-handle Win32 volume
  information hook.

SREV-282 classifies the old Chrome Flash hook as dormant. It does not revive the
registration and does not change volume-info behavior.

## Official Shape

Microsoft documents `GetVolumeInformationW` as retrieving file-system and volume
information for a specified root directory. If `lpRootPathName` is NULL, the
root of the current directory is used.

The output buffers and output pointers are optional. The volume-name and
file-system-name buffer sizes are ignored when the corresponding buffer is not
supplied. Optional output pointers may be NULL when that information is not
required.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw`

## Schema

Local schema:

```text
docs/plan/srev-282-chrome-flash-volume-info-dormant-hook.schema.json
```

Contract id:

```text
CHROME_FLASH_VOLUME_INFO_DORMANT_HOOK
```

## Boundary

```text
inactive file_init registration
  -> no active GetVolumeInformationW hook

inactive file_misc hook body
  -> historical Chrome all-null predicate only
  -> no current runtime edge
```

Any future revival needs a new Windows compatibility proof and a current caller
contract. Until then, active volume-info changes belong to the existing
`NtQueryVolumeInformationFile`, final-path, or by-handle hook owners.

## Topology

```text
GetVolumeInformationW call today
  -> native Win32 API path unless another active owner hooks it

old Chrome Flash block
  -> commented registration
  -> commented hook body
  -> no active Sandboxie interception edge
```

## Logic Risk

The old comments used broad compatibility wording around inactive code. That can
push a future edit toward re-enabling an old application-specific hook without
first proving the current API shape, caller need, and interaction with the
active volume-info owners. Because Microsoft allows NULL root path and optional
output pointers, an all-null output-parameter call is not enough by itself to
define a Sandboxie policy or compatibility rule.

## Fix

Comment-only source clarification. The inactive registration and inactive body
now name SREV-282, state that the hook remains dormant, and point future revival
at a Windows proof and current caller contract. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-282.py` validates the draft-07 schema, official
reference, inactive `file_init.c` registration, inactive `file_misc.c` body,
active owner adjacency through SREV-273 and SREV-279, stale source wording
removal, and ledger fragment.

Runtime gate: none for the current dormant hook state. Any future revival needs
Windows proof covering the actual caller, all-null optional-output call shape,
normal `GetVolumeInformationW` behavior, SREV-273 final-path adjacency,
SREV-279 `NtQueryVolumeInformationFile` adjacency, and by-handle volume-info
hook interaction.
