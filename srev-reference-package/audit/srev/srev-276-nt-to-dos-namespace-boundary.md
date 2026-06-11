# SREV-276: NT-To-DOS Namespace Boundary

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, Microsoft file namespace, MS-DOS device namespace, and `QueryDosDevice` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `SbieDll_TranslateNtToDosPath` caller-visible path presentation |
| Acceptance gate | Targeted checker validates official references, hidden box-root mapping, disabled device fallback boundary, stale workaround/fixme wording removal, and ledger fragment |

## Data

`SbieDll_TranslateNtToDosPath` mutates a path buffer in place and returns
whether it found a caller-visible DOS/Win32 presentation for an NT path. The
function currently handles:

- `\??\` prefixed DOS paths by stripping the prefix;
- MUP paths by converting the NT MUP prefix to UNC-like syntax;
- configured hidden box-root paths by replacing `Dll_BoxFilePath` with
  `Dll_BoxFileDosPath`;
- ordinary drive or UNC mappings through `File_GetDriveForPath` and
  `File_GetDriveForUncPath`;
- a disabled historical `\Device\` to `\\.\` fallback.

## Official Shape

Microsoft documents two namespace families: the NT namespace, where device
objects live under `\Device`, and Win32 namespaces, where drivers expose device
objects through symbolic links in `Global??`.

Microsoft documents MS-DOS device names as junctions in the object namespace.
`QueryDosDevice` can query those junctions and explains that MS-DOS path
conversion uses them to map drive letters and other DOS devices.

Microsoft documents local and global MS-DOS device namespaces. Drive letters and
DOS devices are context-sensitive links, not a lossless textual replacement for
every NT `\Device\...` object path.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file`
- `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-querydosdevicea`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/defining-an-ms-dos-device-name`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/local-and-global-ms-dos-device-names`

## Boundary

```text
NT path buffer
  -> SbieDll_TranslateNtToDosPath
  -> caller-visible DOS/Win32 path only if a known mapping exists
```

The function owns presentation translation, not generic device access policy.
It may translate known Sandboxie roots, MUP paths, drive letters, and UNC drive
links. It must not claim every NT `\Device\...` path has a safe `\\.\...`
presentation.

## Topology

```text
\??\C:\...
  -> strip \??\

\Device\Mup\server\share\...
  -> UNC-like path suffix

Dll_BoxFilePath...
  -> Dll_BoxFileDosPath...

known drive / UNC mapping
  -> File_GetDriveForPath / File_GetDriveForUncPath
  -> drive-letter or UNC presentation

unmapped \Device\...
  -> no generic fallback
  -> return FALSE
```

## Logic Risk

The old comments made two different decisions look like ad-hoc compatibility
workarounds. The hidden box-root branch is a legitimate Sandboxie presentation
mapping from internal NT root to caller-visible DOS root. The disabled
`\Device\` branch is different: converting arbitrary NT device paths to `\\.\`
would cross from path presentation into device namespace policy and has already
been observed as a crash-handler compatibility trap.

## Fix

Comment-only source clarification. The hidden box-root comment now names the
Sandboxie presentation mapping. The disabled `\Device\` fallback comment now
states that generic NT-device to Win32-device conversion is not legal here and
that the disabled fallback is intentionally not used. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-276.py` validates the draft-07 schema, official
references, `SbieDll_TranslateNtToDosPath` owner block, hidden box-root mapping,
drive/UNC mapping, disabled `\Device\` fallback, stale workaround/fixme wording
removal, and ledger fragment.

Runtime gate: Windows path-presentation matrix covering `\??\` DOS paths,
MUP/UNC paths, hidden box-root DOS projection, drive-letter volume paths,
unmapped NT `\Device\` paths, and the Chrome crash-handler path that motivated
keeping the generic device fallback disabled.
