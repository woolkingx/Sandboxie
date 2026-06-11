# SREV-054: ARM64EC NtOpenFile xtajit64 Range Gate

## Data

`Sandboxie/core/dll/file.c` `File_NtOpenFile` has an ARM64EC-only workaround for
calls returning from `xtajit64.dll`. Those calls bypass the Sandboxie
`File_NtCreateFileImpl` path and call the original `NtOpenFile` directly to
avoid an observed `__chkstk_arm64ec` stack-overflow crash.

The bypass decision uses:

```text
ReturnAddress
xtajit64.dll module base
xtajit64.dll module end
```

## Official Shape

Microsoft documents `GetModuleHandleW` as returning a handle to a module already
loaded in the calling process:

```text
https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlew
```

Microsoft documents the PE optional-header `SizeOfImage` as the in-memory image
size including headers:

```text
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
```

The same PE document identifies `IMAGE_FILE_MACHINE_ARM64EC` as the ABI for
native ARM64 and emulated x64 interoperability.

## Schema

Local schema:

```text
docs/plan/srev-054-file-arm64ec-xtajit64-range.schema.json
```

The compatibility bypass may trigger only when the return address is inside the
loaded `xtajit64.dll` image range `[base, base + SizeOfImage)`.

## Topology

```text
loaded xtajit64.dll -> image base/SizeOfImage -> return-address gate -> NtOpenFile bypass
```

The module loader owns the mapped module identity. The PE image header owns the
in-memory image extent. `File_NtOpenFile` owns the compatibility bypass decision.

## Logic Risk

Before this patch, the bypass gate used a hard-coded `0x180000` upper bound and
an externally mismatched `Dll_xtajit64` type. If the real mapped image size
differs from that constant, the hook can either bypass file policy for code
outside the module image or miss real `xtajit64.dll` callers that still need the
ARM64EC stack workaround.

## Fix

`Dll_Ordinal1` now records `Dll_xtajit64` as an integer module base and computes
`Dll_xtajit64_End` from the loaded image's PE `SizeOfImage` after validating DOS
and NT signatures. `File_NtOpenFile` now gates the direct `NtOpenFile` bypass on
`Dll_xtajit64 && Dll_xtajit64_End && ReturnAddress >= base && ReturnAddress < end`.

SREV-267 later removed the stale `TODO: Fix-Me` wording from the
`File_NtOpenFile` bypass block and made this SREV the explicit owner of the
ARM64EC compatibility bypass topology.

## Acceptance Gate

`docs/plan/check-srev-054.py` validates the draft-07 schema, official reference
links, removal of the hard-coded `0x180000` range, typed base/end globals,
PE-header `SizeOfImage` derivation, overflow guard, caller range gate, and
SREV-267 comment-owner adjacency.

Windows gate: ARM64EC process with `xtajit64.dll` loaded should bypass only for
return addresses inside the real mapped `xtajit64.dll` image and should keep the
normal Sandboxie file path for return addresses outside that image.
