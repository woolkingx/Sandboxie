# SREV-240: Aulldvrm Legacy X86 Helper Build Surface

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-239, `Sandboxie/core/drv/aulldvrm.asm` was the top unnamed
reviewable core file. Source readback shows it is a legacy MASM helper for the
32-bit `_aulldvrm` unsigned 64-bit divide/remainder support routine. The file
comments say the routine was needed because `_aulldvrm` was not available on
Windows 2000, and that the body was copied from the WDK CRT `ulldvrm.obj`.

The file is not an active runtime owner in the current project topology:

- `aulldvrm.asm` declares `__aulldvrm proc`, uses 32-bit MASM directives
  `.386p`, `.model flat`, and `.code`, preserves `esi`, computes through
  `eax`, `edx`, `ecx`, `ebx`, and `esi`, returns with `ret 10h`, and exports
  `public __aulldvrm`.
- `ifdef _WIN64` leaves the x64/ARM64 path empty, so the meaningful body is
  the 32-bit MASM path.
- `Sandboxie/core/drv/SboxDrv.vcxproj` still lists `aulldvrm.asm` as a
  `CustomBuild` item and gives Win32 `ml` commands plus x64/ARM64 `ml64
  -D_WIN64` commands.
- The same `CustomBuild` item is excluded from `SbieDebug` and `SbieRelease`
  for `Win32`, `x64`, and `ARM64`, so no object is emitted by the current
  project configuration.
- `Sandboxie/core/drv/SboxDrv.vcxproj.filters` keeps the file visible in the
  project tree.
- A source-tree reference scan finds no direct `__aulldvrm` caller outside
  `aulldvrm.asm` and the project/filter entries.

Existing architecture-specific entries are separate owners. SREV-170 covers
`Sandboxie/core/drv/util_arm.asm` ARM64 driver assembly. SREV-102 covers the
private syscall table scanner boundary. SREV-132 covers the low-level ARM64
entry syscall ABI. None of those entries prove this dormant x86 CRT helper.

## Data

`aulldvrm.asm`, `__aulldvrm`, `_aulldvrm`, `ulldvrm.obj`, `.386p`,
`.model flat`, `ifdef _WIN64`, `ml`, `ml64`, `-D_WIN64`, `ret 10h`,
`SboxDrv.vcxproj`, `SboxDrv.vcxproj.filters`, `SbieDebug|Win32`,
`SbieRelease|Win32`, `SbieDebug|x64`, `SbieRelease|x64`,
`SbieDebug|ARM64`, and `SbieRelease|ARM64`.

## Schema

`AULLDVRM_LEGACY_X86_HELPER_CONTRACT` says:

- `aulldvrm.asm` is a legacy x86 MASM helper for `__aulldvrm`.
- The source body is meaningful only for the non-`_WIN64` MASM path.
- `SboxDrv.vcxproj` owns whether this helper is built.
- The current project excludes this helper from all listed driver
  configurations.
- No current source call site proves runtime dependence on `__aulldvrm`.
- Re-enabling the helper requires a Windows x86 WDK build proof and CRT helper
  ABI proof before behavior claims.

## Topology

```text
SboxDrv.vcxproj
-> CustomBuild Include="aulldvrm.asm"
-> command templates for Win32 ml and x64/ARM64 ml64 -D_WIN64
-> ExcludedFromBuild=true for SbieDebug/SbieRelease on Win32/x64/ARM64
-> no current object emission
-> no current driver link/runtime edge
```

If a future change re-enables the item, the topology changes to:

```text
Win32 driver build
-> ml assembles aulldvrm.asm
-> __aulldvrm exported helper object
-> unresolved compiler/CRT helper reference may bind
-> x86 stack/register ABI must hold
```

That future topology needs a Windows build and ABI proof. It cannot be inferred
from the current excluded project item.

## Logic Risk

The risk is stale topology, not a proven active bug. The file comment points to
an old Windows 2000/WDK CRT compatibility workaround, while the current project
excludes the item everywhere. Treating it as an active ARM64 or x64 helper would
misroute review into the wrong ABI family. Treating it as removed would also be
wrong because the project file still carries commands and filters for it.

The correct owner split is:

- `aulldvrm.asm` owns the legacy helper bytes if the item is ever enabled.
- `SboxDrv.vcxproj` owns the active/inactive build decision.
- Windows x86 MASM/WDK build proof owns any future runtime claim.
- SREV-170, SREV-102, and SREV-132 remain separate architecture/topology
  owners and do not close this file.

## Official Shape

No new Windows runtime behavior is defined by this file while it is excluded
from all project configurations.

Official Microsoft references used as shape constraints:

- `https://learn.microsoft.com/en-us/cpp/assembler/masm/dot-386?view=msvc-170`
  documents `.386` as a 32-bit MASM directive.
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/x86-architecture`
  documents x86 calling-convention preservation and return-value shape.
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/x86-instructions`
  documents `RET #n` as returning while adding `#n` to the stack pointer.
- `https://learn.microsoft.com/en-us/cpp/cpp/stdcall?view=msvc-170` documents
  the Windows x86 callee-cleans-stack calling convention shape.

These references are enough to classify the local source as x86 stack/register
assembly. They do not prove that the helper is needed or safe to re-enable in a
modern driver build.

## Fix

No source patch. This SREV records `aulldvrm.asm` as a dormant legacy x86 helper
build surface and closes it as docs-only coverage. Future cleanup could remove
the excluded project item, but that is a separate maintainer decision and should
not be hidden inside a behavior review.

## Acceptance Gate

`docs/plan/check-srev-240.py` validates the draft-07 schema, legacy x86 MASM
source shape, project build/exclusion topology, filters entry, absence of
source-tree call sites, existing architecture SREV separation, split ledger
fragment, and docs-only classification.

Runtime/build gate: if `aulldvrm.asm` is re-enabled, a Windows x86 WDK driver
build must prove the helper object links only where intended and preserves the
expected x86 stack/register ABI. Current Linux source checks do not prove that
future runtime path.
