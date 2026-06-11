# SREV-055: SYSFER Entry Point Patch Boundary

## Data

`Sandboxie/core/dll/custom.c` `Custom_SYSFER_DLL` nullifies Symantec Endpoint
Protection `SYSFER.DLL` by rewriting the loaded image entry point with:

```text
mov al, 1
ret
```

The patch data is:

```text
loaded module base
PE DOS/NT headers
AddressOfEntryPoint RVA
SizeOfImage
4-byte entry point patch
page protection transition
instruction-cache flush
```

## Official Shape

Microsoft documents the PE format as an image with DOS header, PE signature, and
optional header. The optional header contains the entry point RVA and image size:

```text
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
```

Microsoft documents `VirtualProtect` as changing page protection and states that
code made executable or modified in executable memory requires instruction-cache
coherency through `FlushInstructionCache`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
```

Microsoft documents `FlushInstructionCache` as required when applications
generate or modify code in memory:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
```

## Schema

Local schema:

```text
docs/plan/srev-055-custom-sysfer-entrypoint-patch.schema.json
```

The entry point patch may run only when the target module base is non-null, the
loaded image has valid DOS/NT signatures, and `AddressOfEntryPoint` names a
4-byte writable span inside `[base, base + SizeOfImage)`.

## Topology

```text
loaded SYSFER.DLL -> PE entry point RVA -> bounded patch span -> executable cache coherency
```

The loader owns the module mapping. The PE headers own the entry point and image
extent. `Custom_SYSFER_DLL` owns only the four-byte compatibility patch and must
restore page protection after writing it.

## Logic Risk

Before this patch, `Custom_SYSFER_DLL` trusted `Ldr_OptionalHeader(base)` and
patched `base + AddressOfEntryPoint` without checking `hmodule`, DOS/NT
signature, non-zero entry point, or whether the 4-byte patch fits inside the
loaded image. It also changed executable page protection and wrote code without
flushing the instruction cache or restoring the old protection.

## Fix

`Custom_SYSFER_DLL` now validates the module base, PE DOS signature, PE NT
signature, non-zero entry point RVA, and patch span against `SizeOfImage`. The
source comment points back to this SREV as the bounded entry-point patch owner.
The patch uses `VirtualProtect` over the exact four-byte span, writes the
compatibility return stub, flushes the instruction cache, and restores the
previous page protection.

## Acceptance Gate

`docs/plan/check-srev-055.py` validates the draft-07 schema, official reference
links, PE signature gates, entry point span gate, exact patch span
`VirtualProtect`, instruction-cache flush, old protection restore, owner-boundary
comment, and ledger entry.

Windows gate: loading `SYSFER.DLL` should patch only a valid in-image entry
point, keep the process executable-code cache coherent, restore old page
protection, and safely skip null or malformed module images.
