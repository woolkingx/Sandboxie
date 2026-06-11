# SREV-244: LowLevel DEF Legacy Stub Classification

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-243, `Sandboxie/core/low/LowLevel.def` was the final unnamed
reviewable core file. Source readback shows it contains only:

```text
LIBRARY .TAIL.
```

`Sandboxie/core/low/LowLevel.vcxproj` lists `LowLevel.def` as a `None` item, but
does not select it as a linker `ModuleDefinitionFile`. The active low-level
project topology is a no-entry dynamic library with no default libraries,
special section/base-address constraints, assembly entry files, `init.c`, and
`inject.c`. The built `LowLevel.dll` artifacts are then embedded into `SbieDll`
through `Sandboxie/core/dll/lowlevel.rc`, as documented by SREV-221.

Existing concrete low-level behavior entries are separate owners:

- SREV-132 owns ARM64 / ARM64EC low-level entry and syscall ABI behavior.
- SREV-133 owns the x64 `_Start` nonvolatile-register prelude.
- SREV-106 owns ARM64EC syscall-entry injection routing in `init.c`.
- SREV-221 owns the `SbieDll` resource topology that embeds `LowLevel.dll`.

## Data

`LowLevel.def`, `LIBRARY .TAIL.`, `LowLevel.vcxproj`, `ModuleDefinitionFile`,
`NoEntryPoint`, `BaseAddress`, `RandomizedBaseAddress`, `entry_asm.asm`,
`entry_arm.asm`, `init.c`, `inject.c`, `lowlevel.rc`, `LOWLEVEL32`,
`LOWLEVEL64`, SREV-132, SREV-133, SREV-106, and SREV-221.

## Schema

`LOWLEVEL_DEF_LEGACY_STUB_CONTRACT` says:

- `LowLevel.def` is a legacy DEF stub, not the active linker export table for
  the current LowLevel project.
- `LowLevel.vcxproj` lists the file as a `None` item only.
- The current LowLevel link topology does not set `ModuleDefinitionFile`.
- LowLevel runtime behavior is owned by entry assembly, `init.c`, `inject.c`,
  and `SbieDll` resource embedding, not this DEF stub.
- Removing or reviving the stub is a project cleanup decision requiring
  maintainer/build-system proof.
- Any future export-table claim needs Windows `LowLevel.dll` build and
  `dumpbin /exports` proof.

## Topology

```text
LowLevel.vcxproj
-> DynamicLibrary
-> Link.NoEntryPoint=true
-> no ModuleDefinitionFile
-> entry_asm.asm for Win32/x64
-> entry_arm.asm for ARM64
-> init.c / inject.c
-> LowLevel.dll artifact
-> SboxDll lowlevel.rc LOWLEVEL32/LOWLEVEL64 resource embedding
-> lowlevel_inject.c consumes embedded resource
```

`LowLevel.def` has only this current project edge:

```text
LowLevel.vcxproj
-> None Include="LowLevel.def"
-> no linker export-table edge
```

## Logic Risk

The risk is stale export-topology confusion. `LowLevel.dll` is not an ordinary
export-driven DLL in this project; it is a low-level injected payload with
special entry/bootstrap behavior. Treating `LowLevel.def` as the runtime owner
would hide the actual ABI owners in entry assembly and injection code. Deleting
it without checking old build surfaces could still remove a legacy project
artifact outside the current active linker path.

## Official Shape

No new Windows/API runtime behavior is defined by this stub. MSVC DEF export
shape is already preserved in SREV-136 for the active `SbieDll` export ABI.
This SREV is a local LowLevel build/topology classification.

## Fix

No source patch. This SREV records `LowLevel.def` as a dormant legacy DEF stub
and closes it as docs-only coverage. Future cleanup should either remove it
with maintainer agreement and build-system search proof, or revive it only with
a real `ModuleDefinitionFile` edge and Windows export-table proof.

## Acceptance Gate

`docs/plan/check-srev-244.py` validates the draft-07 schema, stub source shape,
absence of a current `ModuleDefinitionFile` edge, `None` project item topology,
active LowLevel assembly/init/inject topology, existing low-level SREV
ownership, split ledger fragment, and docs-only classification.

Runtime/build gate: none for current project behavior because the stub is not a
selected module-definition file. Any future removal or revival needs Windows
`LowLevel.dll` build and `dumpbin /exports` proof.
