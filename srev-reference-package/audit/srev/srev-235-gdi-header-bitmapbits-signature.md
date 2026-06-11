# SREV-235: GDI Header GetBitmapBits Signature Contract

## Stage

data -> schema -> boundary -> topology -> logic -> action -> verify

## Evidence

After SREV-234, `Sandboxie/core/dll/gdi.h` was the top unnamed reviewable core
file. Source readback showed the header declares GDI function-pointer typedefs
used by `gdi.c` to cache `GetProcAddress` results and by `ole.cpp` to decide
whether Sandboxie should release GDI clipboard storage directly.

`P_GetEnhMetaFileBits`, `P_DeleteObject`, and `P_DeleteEnhMetaFile` matched
their documented Win32 return and parameter shapes. `P_GetBitmapBits` did not:
the local typedef used `UINT (*)(HBITMAP, UINT, LPBYTE)`, while Microsoft
documents `GetBitmapBits` as returning `LONG` and taking `LONG cb` plus
`LPVOID lpvBits`.

## Data

`P_GetBitmapBits`, `__sys_GetBitmapBits`, `GetProcAddress("GetBitmapBits")`,
`Ole_ReleaseStgMedium`, `TYMED_GDI`, `HBITMAP`, `LONG cb`, `LPVOID lpvBits`,
`P_GetEnhMetaFileBits`, `P_DeleteObject`, and `P_DeleteEnhMetaFile`.

## Official Shape

Microsoft documents:

- `GetEnhMetaFileBits(HENHMETAFILE hEMF, UINT nSize, LPBYTE lpData) -> UINT`;
- `GetBitmapBits(HBITMAP hbit, LONG cb, LPVOID lpvBits) -> LONG`;
- `DeleteObject(HGDIOBJ ho) -> BOOL`;
- `DeleteEnhMetaFile(HENHMETAFILE hmf) -> BOOL`.

References:

```text
https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-getenhmetafilebits
https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-getbitmapbits
https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-deleteobject
https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-deleteenhmetafile
```

## Schema

`GDI_HEADER_BITMAPBITS_SIGNATURE_CONTRACT` says:

- `gdi.h` owns the DLL-local GDI function-pointer declarations consumed across
  `gdi.c` and `ole.cpp`.
- `P_GetBitmapBits` must match the documented Win32 shape:
  `LONG (HBITMAP, LONG, LPVOID)`.
- The enhanced-metafile and delete typedefs remain unchanged because they
  already match the documented Win32 shape.
- `gdi.c` may continue to obtain `GetBitmapBits` through `GetProcAddress` and
  store it in `__sys_GetBitmapBits`.
- `ole.cpp` may continue using a zero-size/null-buffer query only as an
  ownership probe before deleting `TYMED_GDI` storage.
- Linux source proof is not Windows `SboxDll` build/runtime proof.

## Topology

```text
gdi.c Gdi_Full_Init_impl
-> GetProcAddress(module, "GetBitmapBits")
-> __sys_GetBitmapBits typed by gdi.h P_GetBitmapBits
-> ole.cpp Ole_ReleaseStgMedium
-> optional __sys_GetBitmapBits(hBitmap, 0, NULL) ownership probe
-> __sys_DeleteObject(hBitmap)
```

The header owns the function-pointer ABI shape. `gdi.c` owns resolution and
hook initialization. `ole.cpp` owns the clipboard storage release decision.

## Logic Risk

The old typedef used the right argument count and 32-bit widths, so the usual
Windows calling convention was unlikely to be broken by register/stack layout.
But the local declaration still contradicted the API contract: signed `LONG`
return/size semantics were flattened into unsigned `UINT`, and the output
buffer was narrowed from generic `LPVOID` to `LPBYTE`. Keeping wrong typedefs
around makes future ownership or buffer-size reasoning use the wrong schema.

## Fix

`P_GetBitmapBits` now matches the documented Win32 signature:

```c
typedef LONG (*P_GetBitmapBits)(
    HBITMAP hBitmap,
    LONG cbBuffer,
    LPVOID lpvBits
    );
```

No `GetProcAddress` topology, OLE release policy, GDI hook installation, printer
retry behavior, font path behavior, or monitor trace behavior changed.

## Acceptance Gate

`docs/plan/check-srev-235.py` validates the draft-07 schema, official
references, corrected `P_GetBitmapBits` typedef, unchanged neighboring GDI
typedefs, `gdi.c` function-pointer resolution, `ole.cpp` release topology,
existing GDI SREV owner coverage, split ledger fragment, and removal of the
old unsigned `P_GetBitmapBits` signature.

Runtime/build gate: Windows `SboxDll` build plus clipboard/OLE `TYMED_GDI`
release smoke proving `GetBitmapBits(hBitmap, 0, NULL)` ownership probing and
`DeleteObject` release behavior still work; no regression in enhanced-metafile
release.
