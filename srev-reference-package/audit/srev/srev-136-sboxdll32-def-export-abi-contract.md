# SREV-136: SboxDll32 DEF Export ABI Contract

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/SboxDll32.def`, `Sandboxie/core/dll/SboxDll64.def`, `Sandboxie/core/dll/SboxDll.vcxproj`, `Sandboxie/core/dll/sbieapi.h`, `Sandboxie/core/dll/sbiedll.h`, Microsoft DEF / EXPORTS / decorated-name references |
| Output artifact | `docs/plan/srev-136-sboxdll32-def-export-abi-contract.schema.json`, `docs/plan/check-srev-136.py`, `docs/plan/check-srev-136.sh`, ledger row |
| Owner | Win32 `SbieDll` export table |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows `dumpbin /exports` runtime/build proof remains required |

## Evidence

`Sandboxie/core/dll/SboxDll32.def` was the highest-ranked unnamed reviewable core file after SREV-135. The Win32 project configurations in `Sandboxie/core/dll/SboxDll.vcxproj` select `SboxDll32.def` as the linker `ModuleDefinitionFile`, while x64, ARM64EC, and ARM64 configurations select `SboxDll64.def`. `SboxDll32.def` contains one ordinal-only export, `Dll_Ordinal1 @1 NONAME`, and 76 public aliases from undecorated `SbieApi_*` / `SbieDll_*` names to x86 decorated internal symbols such as `_SbieDll_RunSandboxed@24`.

Microsoft documents module-definition files as linker input for DLL exports. Microsoft documents `EXPORTS` definitions as `entryname[=internal_name] [@ordinal [NONAME]]`, and says `NONAME` exports by ordinal only. Microsoft documents x86 `__stdcall` C decoration as a leading underscore plus a trailing `@` byte count. Microsoft documents `/DEF` as passing one module-definition file to LINK.

Official references:

- https://learn.microsoft.com/en-us/cpp/build/reference/module-definition-dot-def-files?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/build/reference/exports?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/build/reference/decorated-names?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/build/reference/def-specify-module-definition-file?view=msvc-170

## Data

`SboxDll32.def`, `SboxDll64.def`, `SboxDll.vcxproj`, `ModuleDefinitionFile`, `Win32`, `x64`, `ARM64EC`, `ARM64`, `EXPORTS`, `Dll_Ordinal1 @1 NONAME`, public undecorated aliases, x86 decorated internal names, `SbieApi_*`, `SbieDll_*`, `sbieapi.h`, and `sbiedll.h`.

## Schema

`SBOXDLL32_DEF_EXPORT_ABI_CONTRACT` says:

- `SboxDll32.def` is the Win32 linker-owned public export alias table for `SbieDll`.
- Win32 project configurations select `SboxDll32.def` as the `ModuleDefinitionFile`.
- x64, ARM64EC, and ARM64 project configurations do not select `SboxDll32.def`.
- `Dll_Ordinal1` remains exported by ordinal 1 with `NONAME` for injection startup compatibility.
- Every public Win32 alias in `SboxDll32.def` maps to an x86 decorated internal symbol.
- The x86 decorated internal symbol suffix records the byte count for the stdcall parameter list.
- The DEF file preserves undecorated public `SbieApi` and `SbieDll` names for clients.
- `SboxDll64.def` remains a separate minimal 64-bit export table.

## Topology

The legal Win32 export topology is:

```text
Win32 SboxDll.vcxproj configuration
  -> Link.ModuleDefinitionFile = SboxDll32.def
  -> EXPORTS
  -> Dll_Ordinal1 @1 NONAME
  -> public alias = x86 decorated internal symbol
  -> import library / PE export table
  -> Win32 callers link by stable public alias or ordinal 1 where required
```

The legal non-Win32 topology is:

```text
x64 / ARM64EC / ARM64 SboxDll.vcxproj configuration
  -> Link.ModuleDefinitionFile = SboxDll64.def
  -> minimal ordinal-1 export table
```

## Logic Risk

This file is a binary ABI surface, not ordinary source logic. A wrong alias, ordinal, or decorated byte count can break external Win32 callers even if the C source still compiles. Source review did not expose a surgical local defect in the DEF table; changing it without `dumpbin /exports` proof would be ABI churn. The correct action is to pin the contract and require Windows export-table evidence for future mutation.

## Fix

No source behavior changed. `Sandboxie/core/dll/SboxDll32.def` is now ledger-named with its Win32 DEF export ABI contract and source gate.

## Acceptance Gate

`docs/plan/check-srev-136.py` validates the draft-07 schema, official references, Win32 `ModuleDefinitionFile` selection, non-Win32 `SboxDll64.def` selection, `SboxDll32.def` export count and alias shape, ordinal-1 `NONAME` preservation, selected x86 decorated byte-count examples, public header linkage evidence, separate minimal `SboxDll64.def`, and ledger entry. `docs/plan/check-srev-136.sh` is the matrix wrapper.

Runtime/build gate: Windows Win32 `SboxDll` build, `dumpbin /exports` proving `Dll_Ordinal1` is ordinal-only `NONAME` at ordinal 1, `dumpbin /exports` proving the public undecorated aliases resolve to expected x86 decorated internals, and client import-library smoke proving existing Win32 callers still link by public alias.
