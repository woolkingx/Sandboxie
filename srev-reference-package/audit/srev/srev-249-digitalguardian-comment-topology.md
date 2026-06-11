# SREV-249: Digital Guardian Comment Topology

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/dllmain.c`, `Sandboxie/core/dll/file.c`, `Sandboxie/core/dll/dll.h`, `Sandboxie/core/dll/ldr.c`, SREV-088, Microsoft `GetModuleHandleA` and `DllMain` references |
| Output artifact | `docs/plan/srev-249-digitalguardian-comment-topology.schema.json`, `docs/plan/check-srev-249.py`, `docs/plan/check-srev-249.sh`, ledger fragment, comment-only source clarification |
| Owner | Digital Guardian module-presence and file-policy compatibility topology |
| Acceptance gate | targeted source checker plus core coverage/diff checkpoint |

## Evidence

SREV-088 already classified `Dll_DigitalGuardian` as a module-presence flag:

```text
dllmain.c GetModuleHandleA("DgApi64.dll" / "DgApi.dll")
  -> Dll_DigitalGuardian global module-presence flag
  -> ldr.c DigitalGuardian_Init when module loads
  -> file.c Digital Guardian file-policy compatibility checks
```

The source still had anonymous `$Workaround$ - 3rd party fix` labels at the
definition, process-attach seed, loader callback, and two file-policy branches.
Those labels hid the actual owner boundary and kept the comment-risk queue hot
even though the local behavior had already been classified.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlea
- https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain

## Data

`Dll_DigitalGuardian`, `GetModuleHandleA("DgApi64.dll")`,
`GetModuleHandleA("DgApi.dll")`, `DigitalGuardian_Init`, `DllMain`,
`FILE_DELETE_ON_CLOSE`, `PATH_IS_WRITE`, `PATH_IS_CLOSED`,
`NtQueryFullAttributesFile`, and SREV-088 module-presence topology.

## Schema

`DIGITALGUARDIAN_COMMENT_TOPOLOGY` says:

- `Dll_DigitalGuardian` is module-presence evidence, not module ownership.
- `DllMain` may seed the flag only when the Digital Guardian DLL is already
  mapped in the current process.
- `DigitalGuardian_Init` updates the same flag when the loader observes the
  module later.
- `file.c` owns Digital Guardian file-policy compatibility branches; the flag
  is only a decision input there.
- The comment clarification must not change detection, loader callback,
  file-policy branch conditions, or return values.

## Topology

Process attach path:

```text
DllMain(DLL_PROCESS_ATTACH)
  -> GetModuleHandleA(DgApi64.dll / DgApi.dll)
  -> Dll_DigitalGuardian presence flag
```

Loader callback path:

```text
ldr.c module table observes dgapi*.dll
  -> DigitalGuardian_Init(hModule)
  -> Dll_DigitalGuardian presence flag
```

File-policy path:

```text
file.c delete-on-close and true-path attribute checks
  -> read Dll_DigitalGuardian
  -> choose Digital Guardian compatibility branch or direct true-file query
```

## Logic Risk

The old labels made a cross-file module-presence topology look like unrelated
third-party residue. That increases the chance of a future patch treating the
`HMODULE` as a lifetime-owned reference, removing the early seed while keeping
the loader callback, or altering the file-policy branch without understanding
why the module flag exists.

The legal improvement is comment-only: name the data owner, the loader seed,
the loader callback, and the file-policy consumers without changing runtime
behavior.

## Fix

Comment-only source clarification:

- `dllmain.c` definition now calls `Dll_DigitalGuardian` a
  module-presence flag, not a reference owner.
- `DllMain(DLL_PROCESS_ATTACH)` now names the early seed before loader callback
  observation.
- `file.c` now names the Digital Guardian delete-on-close and true-path
  attribute-query branches.
- `DigitalGuardian_Init` now names the loader callback role.

## Acceptance Gate

`docs/plan/check-srev-249.py` validates the draft-07 schema, official reference
links, SREV-088 adjacency, `GetModuleHandleA` seed shape, `ldr.c` callback
shape, `file.c` policy consumers, removal of stale anonymous labels from the
Digital Guardian source sites, and the ledger fragment.

Runtime gate: not required for this comment-only clarification. Existing
Digital Guardian runtime behavior remains a Windows compatibility gate owned by
the earlier behavior-changing SREV rows.
