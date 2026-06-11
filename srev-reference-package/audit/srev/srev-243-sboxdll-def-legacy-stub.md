# SREV-243: SboxDll DEF Legacy Stub Classification

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-242, `Sandboxie/core/dll/SboxDll.def` was the top unnamed
reviewable core file. Source readback shows it is a three-line legacy DEF stub:

```text
LIBRARY SboxDll
#define SBIEDLL_LIBRARY_STATEMENT_ISSUED
#include "sbiedll.def"
```

Current project topology does not use this file as a linker export owner.
`Sandboxie/core/dll/SboxDll.vcxproj` selects `SboxDll32.def` for Win32 and
`SboxDll64.def` for x64, ARM64EC, and ARM64. The project lists
`SboxDll32.def` and `SboxDll64.def` as `None` items and filter entries, but
does not list `SboxDll.def`. A repo file scan finds no `sbiedll.def` include
target, so `SboxDll.def` is not a complete standalone DEF input in this
worktree.

SREV-136 already owns the active `SbieDll` export ABI contract for
`SboxDll32.def` and `SboxDll64.def`, including official MSVC DEF / EXPORTS /
decorated-name references and Windows `dumpbin /exports` runtime gates.

## Data

`SboxDll.def`, `SboxDll32.def`, `SboxDll64.def`, `sbiedll.def`,
`SboxDll.vcxproj`, `SboxDll.vcxproj.filters`, `ModuleDefinitionFile`,
`LIBRARY SboxDll`, `SBIEDLL_LIBRARY_STATEMENT_ISSUED`, `#include`, `EXPORTS`,
`Dll_Ordinal1 @1 NONAME`, SREV-136, and MSVC `/DEF`.

## Schema

`SBOXDLL_DEF_LEGACY_STUB_CONTRACT` says:

- `SboxDll.def` is a legacy DEF preprocessor stub, not the active linker export
  table for current project builds.
- The active Win32 export table is `SboxDll32.def`.
- The active x64, ARM64EC, and ARM64 export table is `SboxDll64.def`.
- `SboxDll.def` is incomplete in this worktree because its included
  `sbiedll.def` target is absent.
- Export ABI behavior changes must target `SboxDll32.def` / `SboxDll64.def`
  and SREV-136, not this stub.
- Removing or reviving the stub is a project cleanup decision that needs
  maintainer/build-system proof, not a runtime behavior patch.

## Topology

```text
current active build topology
-> SboxDll.vcxproj
-> Link.ModuleDefinitionFile
-> Win32: SboxDll32.def
-> x64 / ARM64EC / ARM64: SboxDll64.def
-> import library / PE export table
```

`SboxDll.def` has no current project edge:

```text
SboxDll.def
-> LIBRARY SboxDll
-> #include "sbiedll.def"
-> missing include target in this worktree
-> no SboxDll.vcxproj ModuleDefinitionFile edge
-> no current export-table proof
```

## Logic Risk

The risk is stale export-topology confusion. If a reviewer treats
`SboxDll.def` as the active export ABI owner, they may audit the wrong file and
miss the real 32-bit/64-bit DEF tables. If they delete it without checking old
build surfaces, they may remove a legacy compatibility input that is outside
the current vcxproj path.

## Official Shape

No new Windows/API runtime behavior is defined by this stub. SREV-136 already
records Microsoft module-definition, `EXPORTS`, decorated-name, and `/DEF`
references for the active export ABI. This SREV is a local build/topology
classification.

## Fix

No source patch. This SREV records `SboxDll.def` as a dormant legacy DEF stub
and closes it as docs-only coverage. Future cleanup should either remove it
with maintainer agreement and build-system search proof, or revive it only with
the missing include target and a Windows export-table proof.

## Acceptance Gate

`docs/plan/check-srev-243.py` validates the draft-07 schema, legacy stub source
shape, missing include target, absence from current project/filter build edges,
active `SboxDll32.def` / `SboxDll64.def` ModuleDefinitionFile topology,
SREV-136 ownership, split ledger fragment, and docs-only classification.

Runtime/build gate: none for current project behavior because the stub is not
selected by `SboxDll.vcxproj`. Any future removal or revival needs Windows
`SbieDll` build and `dumpbin /exports` proof.
