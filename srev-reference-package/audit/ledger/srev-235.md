---
kind: srev-ledger-entry
id: SREV-235
title: GDI Header GetBitmapBits Signature Contract
status: patched-source-level-after-official-gdi-signature-review-needs-windows-dll-build-runtime-proof
owner: Sandboxie/core/dll/gdi.h
additional_owners:
  - Sandboxie/core/dll/gdi.c
  - Sandboxie/core/dll/ole.cpp
spec: docs/plan/srev-235-gdi-header-bitmapbits-signature.md
schema: docs/plan/srev-235-gdi-header-bitmapbits-signature.schema.json
checker: docs/plan/check-srev-235.py
runtime_gate: Windows SboxDll build plus clipboard/OLE TYMED_GDI release smoke proving GetBitmapBits(hBitmap, 0, NULL) ownership probing and DeleteObject release behavior still work; no regression in enhanced-metafile release.
---

### SREV-235: GDI Header GetBitmapBits Signature Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official GDI signature review; needs Windows DLL build/runtime proof |
| Evidence | `Sandboxie/core/dll/gdi.h` was the top unnamed reviewable core file after SREV-234. It declares GDI function-pointer typedefs used by `gdi.c` to cache `GetProcAddress` results and by `ole.cpp` to release selected GDI clipboard storage directly. `P_GetEnhMetaFileBits`, `P_DeleteObject`, and `P_DeleteEnhMetaFile` matched their documented Win32 shapes. `P_GetBitmapBits` did not: it used `UINT (*)(HBITMAP, UINT, LPBYTE)`, while Microsoft documents `GetBitmapBits` as `LONG (HBITMAP, LONG, LPVOID)`. |
| Data | `P_GetBitmapBits`, `__sys_GetBitmapBits`, `GetProcAddress("GetBitmapBits")`, `Ole_ReleaseStgMedium`, `TYMED_GDI`, `HBITMAP`, `LONG cb`, `LPVOID lpvBits`, `P_GetEnhMetaFileBits`, `P_DeleteObject`, and `P_DeleteEnhMetaFile`. |
| Schema | `GDI_HEADER_BITMAPBITS_SIGNATURE_CONTRACT` says `gdi.h` owns the DLL-local GDI function-pointer declarations consumed across `gdi.c` and `ole.cpp`; `P_GetBitmapBits` must match the documented Win32 shape `LONG (HBITMAP, LONG, LPVOID)`; neighboring enhanced-metafile/delete typedefs remain unchanged; `gdi.c` may continue to resolve `GetBitmapBits` through `GetProcAddress`; and `ole.cpp` may continue using a zero-size/null-buffer query only as an ownership probe before deleting `TYMED_GDI` storage. |
| Topology | `gdi.c Gdi_Full_Init_impl -> GetProcAddress(module, "GetBitmapBits") -> __sys_GetBitmapBits typed by gdi.h P_GetBitmapBits -> ole.cpp Ole_ReleaseStgMedium -> optional __sys_GetBitmapBits(hBitmap, 0, NULL) ownership probe -> __sys_DeleteObject(hBitmap)`. |
| Logic Risk | The old typedef used the right argument count and 32-bit widths, so the usual Windows calling convention was unlikely to be broken by register/stack layout. But the local declaration contradicted the API contract: signed `LONG` return/size semantics were flattened into unsigned `UINT`, and the output buffer was narrowed from generic `LPVOID` to `LPBYTE`. Keeping wrong typedefs around makes future ownership or buffer-size reasoning use the wrong schema. |
| Official Shape | `docs/plan/srev-235-gdi-header-bitmapbits-signature.md` records Microsoft `GetEnhMetaFileBits`, `GetBitmapBits`, `DeleteObject`, and `DeleteEnhMetaFile` references. `docs/plan/srev-235-gdi-header-bitmapbits-signature.schema.json` records the JSON Schema draft-07 local `GDI_HEADER_BITMAPBITS_SIGNATURE_CONTRACT`. |
| Fix | `P_GetBitmapBits` now matches the documented Win32 signature: `LONG (HBITMAP, LONG, LPVOID)`. No `GetProcAddress` topology, OLE release policy, GDI hook installation, printer retry behavior, font path behavior, or monitor trace behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-235.py` validates the draft-07 schema, official references, corrected `P_GetBitmapBits` typedef, unchanged neighboring GDI typedefs, `gdi.c` function-pointer resolution, `ole.cpp` release topology, existing GDI SREV owner coverage, split ledger fragment, and removal of the old unsigned `P_GetBitmapBits` signature; `docs/plan/check-srev-235.sh` is the targeted wrapper. Runtime/build gate: Windows `SboxDll` build plus clipboard/OLE `TYMED_GDI` release smoke proving `GetBitmapBits(hBitmap, 0, NULL)` ownership probing and `DeleteObject` release behavior still work; no regression in enhanced-metafile release. |
