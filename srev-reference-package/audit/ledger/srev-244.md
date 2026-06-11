---
kind: srev-ledger-entry
id: SREV-244
title: LowLevel DEF Legacy Stub Classification
status: docs-only-source-topology-reviewed-dormant-legacy-stub
owner: Sandboxie/core/low/LowLevel.def
additional_owners:
  - Sandboxie/core/low/LowLevel.vcxproj
  - Sandboxie/core/low/entry_asm.asm
  - Sandboxie/core/low/entry_arm.asm
  - Sandboxie/core/low/init.c
  - Sandboxie/core/low/inject.c
  - Sandboxie/core/dll/lowlevel.rc
  - docs/plan/ledger/srev-132.md
  - docs/plan/ledger/srev-133.md
  - docs/plan/ledger/srev-106.md
  - docs/plan/ledger/srev-221.md
spec: docs/plan/srev-244-lowlevel-def-legacy-stub.md
schema: docs/plan/srev-244-lowlevel-def-legacy-stub.schema.json
checker: docs/plan/check-srev-244.py
runtime_gate: None for current project behavior because the stub is not a selected module-definition file. Any future removal or revival needs Windows LowLevel.dll build and dumpbin /exports proof.
---

### SREV-244: LowLevel DEF Legacy Stub Classification

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; dormant legacy stub |
| Evidence | `Sandboxie/core/low/LowLevel.def` was the final unnamed reviewable core file after SREV-243. Source readback shows it contains only `LIBRARY .TAIL.`. `LowLevel.vcxproj` lists `LowLevel.def` as a `None` item, but does not select it as a linker `ModuleDefinitionFile`. The active low-level project topology is a no-entry dynamic library with no default libraries, special section/base-address constraints, assembly entry files, `init.c`, and `inject.c`. The built `LowLevel.dll` artifacts are then embedded into `SbieDll` through `Sandboxie/core/dll/lowlevel.rc`, as documented by SREV-221. |
| Data | `LowLevel.def`, `LIBRARY .TAIL.`, `LowLevel.vcxproj`, `ModuleDefinitionFile`, `NoEntryPoint`, `BaseAddress`, `RandomizedBaseAddress`, `entry_asm.asm`, `entry_arm.asm`, `init.c`, `inject.c`, `lowlevel.rc`, `LOWLEVEL32`, `LOWLEVEL64`, SREV-132, SREV-133, SREV-106, and SREV-221. |
| Schema | `LOWLEVEL_DEF_LEGACY_STUB_CONTRACT` says `LowLevel.def` is a legacy DEF stub, not the active linker export table for the current LowLevel project; `LowLevel.vcxproj` lists the file as a `None` item only; the current LowLevel link topology does not set `ModuleDefinitionFile`; LowLevel runtime behavior is owned by entry assembly, `init.c`, `inject.c`, and `SbieDll` resource embedding, not this DEF stub; removing or reviving the stub is a project cleanup decision requiring maintainer/build-system proof; and any future export-table claim needs Windows `LowLevel.dll` build and `dumpbin /exports` proof. |
| Topology | `LowLevel.vcxproj -> DynamicLibrary -> Link.NoEntryPoint=true -> no ModuleDefinitionFile -> entry_asm.asm for Win32/x64 -> entry_arm.asm for ARM64 -> init.c / inject.c -> LowLevel.dll artifact -> SboxDll lowlevel.rc LOWLEVEL32/LOWLEVEL64 resource embedding -> lowlevel_inject.c consumes embedded resource`. `LowLevel.def` has only this current project edge: `LowLevel.vcxproj -> None Include="LowLevel.def" -> no linker export-table edge`. |
| Logic Risk | The risk is stale export-topology confusion. `LowLevel.dll` is not an ordinary export-driven DLL in this project; it is a low-level injected payload with special entry/bootstrap behavior. Treating `LowLevel.def` as the runtime owner would hide the actual ABI owners in entry assembly and injection code. Deleting it without checking old build surfaces could still remove a legacy project artifact outside the current active linker path. |
| Official Shape | No new Windows/API runtime behavior is defined by this stub. MSVC DEF export shape is already preserved in SREV-136 for the active `SbieDll` export ABI. This SREV is a local LowLevel build/topology classification. |
| Fix | No source patch. This SREV records `LowLevel.def` as a dormant legacy DEF stub and closes it as docs-only coverage. Future cleanup should either remove it with maintainer agreement and build-system search proof, or revive it only with a real `ModuleDefinitionFile` edge and Windows export-table proof. |
| Acceptance Gate | `docs/plan/check-srev-244.py` validates the draft-07 schema, stub source shape, absence of a current `ModuleDefinitionFile` edge, `None` project item topology, active LowLevel assembly/init/inject topology, existing low-level SREV ownership, split ledger fragment, and docs-only classification; `docs/plan/check-srev-244.sh` is the targeted wrapper. Runtime/build gate: none for current project behavior because the stub is not a selected module-definition file. Any future removal or revival needs Windows `LowLevel.dll` build and `dumpbin /exports` proof. |
