---
kind: srev-ledger-entry
id: SREV-136
title: SboxDll32 DEF Export ABI Contract
status: reviewed-source-needs-windows-export-table-proof
owner: Sandboxie/core/dll/SboxDll32.def
spec: docs/plan/srev-136-sboxdll32-def-export-abi-contract.md
schema: docs/plan/srev-136-sboxdll32-def-export-abi-contract.schema.json
checker: docs/plan/check-srev-136.py
runtime_gate: Windows Win32 dumpbin exports and client import-library proof
---

### SREV-136: SboxDll32 DEF Export ABI Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | reviewed source-level ABI/export classification after official MSVC DEF / EXPORTS / decorated-name review; needs Windows Win32 export-table proof |
| Evidence | `Sandboxie/core/dll/SboxDll32.def` was the highest-ranked unnamed reviewable core file after SREV-135. The Win32 project configurations in `Sandboxie/core/dll/SboxDll.vcxproj` select `SboxDll32.def` as the linker `ModuleDefinitionFile`, while x64, ARM64EC, and ARM64 configurations select `SboxDll64.def`. `SboxDll32.def` contains one ordinal-only export, `Dll_Ordinal1 @1 NONAME`, and 76 public aliases from undecorated `SbieApi_*` / `SbieDll_*` names to x86 decorated internal symbols such as `_SbieDll_RunSandboxed@24`. Microsoft documents module-definition files as linker input for DLL exports; documents `EXPORTS` definitions as `entryname[=internal_name] [@ordinal [NONAME]]`; documents x86 `__stdcall` C decoration as a leading underscore plus a trailing `@` byte count; and documents `/DEF` as passing one module-definition file to LINK. |
| Data | `Sandboxie/core/dll/SboxDll32.def`, `Sandboxie/core/dll/SboxDll64.def`, `Sandboxie/core/dll/SboxDll.vcxproj`, `Sandboxie/core/dll/sbieapi.h`, `Sandboxie/core/dll/sbiedll.h`, `ModuleDefinitionFile`, `Win32`, `x64`, `ARM64EC`, `ARM64`, `EXPORTS`, `Dll_Ordinal1 @1 NONAME`, public undecorated aliases, x86 decorated internal names, `SbieApi_*`, and `SbieDll_*`. |
| Schema | `SBOXDLL32_DEF_EXPORT_ABI_CONTRACT` says `SboxDll32.def` is the Win32 linker-owned public export alias table for `SbieDll`; Win32 project configurations select `SboxDll32.def` as the `ModuleDefinitionFile`; x64, ARM64EC, and ARM64 project configurations do not select `SboxDll32.def`; `Dll_Ordinal1` remains exported by ordinal 1 with `NONAME` for injection startup compatibility; every public Win32 alias maps to an x86 decorated internal symbol; the x86 decorated internal symbol suffix records the byte count for the stdcall parameter list; the DEF file preserves undecorated public `SbieApi` and `SbieDll` names for clients; and `SboxDll64.def` remains a separate minimal 64-bit export table. |
| Topology | Legal Win32 export flow is Win32 `SboxDll.vcxproj` configuration, `Link.ModuleDefinitionFile = SboxDll32.def`, `EXPORTS`, `Dll_Ordinal1 @1 NONAME`, public alias to x86 decorated internal symbol, import library / PE export table, then Win32 callers link by stable public alias or ordinal 1 where required. Legal non-Win32 flow is x64 / ARM64EC / ARM64 project configuration, `Link.ModuleDefinitionFile = SboxDll64.def`, then the minimal ordinal-1 export table. |
| Logic Risk | This file is a binary ABI surface, not ordinary source logic. A wrong alias, ordinal, or decorated byte count can break external Win32 callers even if the C source still compiles. Source review did not expose a surgical local defect in the DEF table; changing it without `dumpbin /exports` proof would be ABI churn. The correct action is to pin the contract and require Windows export-table evidence for future mutation. |
| Official Shape | `docs/plan/srev-136-sboxdll32-def-export-abi-contract.md` records Microsoft DEF, `EXPORTS`, decorated-name, and `/DEF` references. `docs/plan/srev-136-sboxdll32-def-export-abi-contract.schema.json` records the JSON Schema draft-07 local `SBOXDLL32_DEF_EXPORT_ABI_CONTRACT` contract. |
| Fix | No source behavior changed. `Sandboxie/core/dll/SboxDll32.def` is now ledger-named with its Win32 DEF export ABI contract and source gate. |
| Acceptance Gate | `docs/plan/check-srev-136.py` validates the draft-07 schema, official references, Win32 `ModuleDefinitionFile` selection, non-Win32 `SboxDll64.def` selection, `SboxDll32.def` export count and alias shape, ordinal-1 `NONAME` preservation, selected x86 decorated byte-count examples, public header linkage evidence, separate minimal `SboxDll64.def`, and ledger entry; `docs/plan/check-srev-136.sh` is the matrix wrapper. Runtime/build gate: Windows Win32 `SboxDll` build, `dumpbin /exports` proving `Dll_Ordinal1` is ordinal-only `NONAME` at ordinal 1, `dumpbin /exports` proving the public undecorated aliases resolve to expected x86 decorated internals, and client import-library smoke proving existing Win32 callers still link by public alias. |
