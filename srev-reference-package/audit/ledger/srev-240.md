---
kind: srev-ledger-entry
id: SREV-240
title: Aulldvrm Legacy X86 Helper Build Surface
status: docs-only-source-topology-reviewed-dormant-build-surface-needs-windows-x86-build-proof-if-reenabled
owner: Sandboxie/core/drv/aulldvrm.asm
additional_owners:
  - Sandboxie/core/drv/SboxDrv.vcxproj
  - Sandboxie/core/drv/SboxDrv.vcxproj.filters
  - docs/plan/ledger/srev-170.md
  - docs/plan/ledger/srev-102.md
  - docs/plan/ledger/srev-132.md
spec: docs/plan/srev-240-aulldvrm-legacy-x86-helper.md
schema: docs/plan/srev-240-aulldvrm-legacy-x86-helper.schema.json
checker: docs/plan/check-srev-240.py
runtime_gate: If aulldvrm.asm is re-enabled, a Windows x86 WDK driver build must prove the helper object links only where intended and preserves the expected x86 stack/register ABI. Current Linux source checks do not prove that future runtime path.
---

### SREV-240: Aulldvrm Legacy X86 Helper Build Surface

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; dormant build surface; needs Windows x86 build proof if re-enabled |
| Evidence | `Sandboxie/core/drv/aulldvrm.asm` was the top unnamed reviewable core file after SREV-239. Source readback shows it is a legacy MASM helper for the 32-bit `_aulldvrm` unsigned 64-bit divide/remainder support routine. The file comments say the routine was needed because `_aulldvrm` was not available on Windows 2000, and that the body was copied from the WDK CRT `ulldvrm.obj`. The project still lists the file as a `CustomBuild` item and filter entry, but excludes the item from `SbieDebug` and `SbieRelease` for `Win32`, `x64`, and `ARM64`; a source-tree scan finds no direct `__aulldvrm` caller outside `aulldvrm.asm` and the project/filter entries. |
| Data | `aulldvrm.asm`, `__aulldvrm`, `_aulldvrm`, `ulldvrm.obj`, `.386p`, `.model flat`, `ifdef _WIN64`, `ml`, `ml64`, `-D_WIN64`, `ret 10h`, `SboxDrv.vcxproj`, `SboxDrv.vcxproj.filters`, `SbieDebug|Win32`, `SbieRelease|Win32`, `SbieDebug|x64`, `SbieRelease|x64`, `SbieDebug|ARM64`, and `SbieRelease|ARM64`. |
| Schema | `AULLDVRM_LEGACY_X86_HELPER_CONTRACT` says `aulldvrm.asm` is a legacy x86 MASM helper for `__aulldvrm`; the source body is meaningful only for the non-`_WIN64` MASM path; `SboxDrv.vcxproj` owns whether this helper is built; the current project excludes this helper from all listed driver configurations; no current source call site proves runtime dependence on `__aulldvrm`; and re-enabling the helper requires a Windows x86 WDK build proof and CRT helper ABI proof before behavior claims. |
| Topology | `SboxDrv.vcxproj -> CustomBuild Include="aulldvrm.asm" -> command templates for Win32 ml and x64/ARM64 ml64 -D_WIN64 -> ExcludedFromBuild=true for SbieDebug/SbieRelease on Win32/x64/ARM64 -> no current object emission -> no current driver link/runtime edge`. If re-enabled: `Win32 driver build -> ml assembles aulldvrm.asm -> __aulldvrm exported helper object -> unresolved compiler/CRT helper reference may bind -> x86 stack/register ABI must hold`. |
| Logic Risk | The risk is stale topology, not a proven active bug. The file comment points to an old Windows 2000/WDK CRT compatibility workaround, while the current project excludes the item everywhere. Treating it as an active ARM64 or x64 helper would misroute review into the wrong ABI family; treating it as removed would also be wrong because the project file still carries commands and filters for it. |
| Official Shape | No new Windows runtime behavior is defined by this file while it is excluded from all project configurations. Microsoft MASM `.386`, x86 calling-convention/register, x86 `RET #n`, and `__stdcall` documentation are enough to classify the source as x86 stack/register assembly, but do not prove that the helper is needed or safe to re-enable in a modern driver build. |
| Fix | No source patch. This SREV records `aulldvrm.asm` as a dormant legacy x86 helper build surface and closes it as docs-only coverage. Future cleanup could remove the excluded project item, but that is a separate maintainer decision and should not be hidden inside a behavior review. |
| Acceptance Gate | `docs/plan/check-srev-240.py` validates the draft-07 schema, legacy x86 MASM source shape, project build/exclusion topology, filters entry, absence of source-tree call sites, existing architecture SREV separation, split ledger fragment, and docs-only classification; `docs/plan/check-srev-240.sh` is the targeted wrapper. Runtime/build gate: if `aulldvrm.asm` is re-enabled, a Windows x86 WDK driver build must prove the helper object links only where intended and preserves the expected x86 stack/register ABI. Current Linux source checks do not prove that future runtime path. |
