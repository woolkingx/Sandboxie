---
kind: srev-ledger-entry
id: SREV-054
title: ARM64EC NtOpenFile xtajit64 Range Gate
status: patched-source-level-after-official-getmodulehandlew-pe-sizeofimage-and-local-ar
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-054-file-arm64ec-xtajit64-range.md
schema: docs/plan/srev-054-file-arm64ec-xtajit64-range.schema.json
checker: docs/plan/check-srev-054.py
runtime_gate: "ARM64EC process with `xtajit64.dll` loaded, return address inside image bypasses without stack overflow; return address outside image stays on normal Sandboxie file path; unloaded/invalid image range disables the bypass"
---
### SREV-054: ARM64EC NtOpenFile xtajit64 Range Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official GetModuleHandleW/PE SizeOfImage and local ARM64EC NtOpenFile bypass analysis; needs Windows ARM64EC runtime proof |
| Evidence | `Sandboxie/core/dll/file.c` `File_NtOpenFile` had a source comment saying ARM64EC `xtajit64.dll` calls to `NtOpenFile` can trigger `__chkstk_arm64ec` stack overflow, so the hook bypasses `File_NtCreateFileImpl` and calls `__sys_NtOpenFile` directly. The bypass gate used `Dll_xtajit64 + 0x180000` as a hard-coded module range, while `Dll_xtajit64` was stored as `void*` in `dllmain.c` and declared as `UINT_PTR` in `file.c`. |
| Data | Captured return address, loaded `xtajit64.dll` module base, PE image `SizeOfImage`, computed module end, and the ARM64EC direct `NtOpenFile` compatibility bypass decision. |
| Schema | `FILE_ARM64EC_XTAJIT64_RANGE_GATE` says the bypass may trigger only when `ReturnAddress` is inside the half-open loaded-image range `[base, base + SizeOfImage)`. A missing or invalid base/end disables the bypass. |
| Topology | The loader maps `xtajit64.dll`; `Dll_Ordinal1` captures the module base and PE image extent; `File_NtOpenFile` uses that owner-local range to decide whether the ARM64EC compatibility bypass is legal. |
| Logic Risk | A hard-coded range can either bypass Sandboxie file policy for a return address outside the real module image or miss a real `xtajit64.dll` caller if the mapped image is larger than the constant. The type mismatch hides the fact that this is an address-range contract, not an opaque module handle contract. |
| Official Shape | `docs/plan/srev-054-file-arm64ec-xtajit64-range.md` records Microsoft `GetModuleHandleW` and PE `SizeOfImage` references. `docs/plan/srev-054-file-arm64ec-xtajit64-range.schema.json` records the JSON Schema draft-07 local `FILE_ARM64EC_XTAJIT64_RANGE_GATE` contract. |
| Fix | `Dll_Ordinal1` now stores `Dll_xtajit64` as `UINT_PTR`, computes `Dll_xtajit64_End` from the loaded image's PE `SizeOfImage` after DOS/NT signature checks and overflow guard, and `File_NtOpenFile` gates the direct `NtOpenFile` bypass on `base <= ReturnAddress < end`. SREV-267 later removed the stale `TODO: Fix-Me` wording and made this SREV the explicit comment owner for the bypass topology. |
| Acceptance Gate | `docs/plan/check-srev-054.py` validates the draft-07 schema, official references, typed base/end globals, PE-header extent derivation, removal of the `0x180000` magic range, overflow guard, caller range gate, SREV-267 comment-owner adjacency, and ledger entry; `docs/plan/check-srev-054.sh` is the targeted wrapper. Windows gate: ARM64EC process with `xtajit64.dll` loaded, return address inside image bypasses without stack overflow; return address outside image stays on normal Sandboxie file path; unloaded/invalid image range disables the bypass. |
