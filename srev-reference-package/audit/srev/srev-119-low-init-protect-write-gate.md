# SREV-119 Low Init Protect Write Gate

## Data

Owner file:

```text
Sandboxie/core/low/init.c
```

Reviewed nodes:

```text
WriteMemorySafe
InitSyscalls
DisableCHPE
NtProtectVirtualMemory
NtFlushInstructionCache
PAGE_EXECUTE_READWRITE
OldProtect
SystemService
ZwXxxPtr
RtlImageOptionsEx_tramp
RtlImageOptionsEx
```

Related existing gates:

```text
docs/plan/srev-106-low-inject-arm64ec-syscall-entrypoint.md
docs/plan/check-srev-106.sh
```

## Schema

`LOW_INIT_PROTECT_WRITE_GATE` defines these local contracts:

- Any `init.c` code/data patch that first changes page protection through
  `NtProtectVirtualMemory(..., PAGE_EXECUTE_READWRITE, &OldProtect)` must check
  the returned `NTSTATUS` before writing through that region.
- `OldProtect` is initialized before each protection-change attempt and is used
  for restore only after the writable-protection call succeeds.
- `WriteMemorySafe` fails closed when the protection change fails.
- `InitSyscalls` skips the current syscall export when its target stub cannot
  be made writable, then continues with the next syscall record.
- `DisableCHPE` returns before copying trampoline bytes or target detour bytes
  when the relevant region cannot be made writable.
- This SREV does not change syscall selection, detour bytes, ARM64EC wrapper
  routing, CHPE policy, or instruction-cache flush placement.

## Topology

```text
low/init.c bootstrap data
  -> NtProtectVirtualMemory PAGE_EXECUTE_READWRITE gate
      -> checked NTSTATUS
          -> local byte write / memcpy / detour patch
          -> restore OldProtect
          -> NtFlushInstructionCache for executable code patches
```

## Logic Risk

The old code treated the protection change as infallible. If
`NtProtectVirtualMemory` failed, `WriteMemorySafe`, `InitSyscalls`, and
`DisableCHPE` still wrote through the target pointer. That is not a legal local
transition: the write depends on the region being made writable first. It also
left `OldProtect` as an uninitialized restore value on the failure path.

This is a bootstrap/low-level path, so the fix stays fail-closed and local. It
does not add logging, allocation, or new owner edges inside early init.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-nt-and-zw-versions-of-the-native-system-services-routines

## Fix

`WriteMemorySafe`, `InitSyscalls`, and `DisableCHPE` now store the
`NtProtectVirtualMemory` return value, initialize `OldProtect`, and write only
after `NT_SUCCESS(status)`.

If `WriteMemorySafe` cannot make the requested region writable, it returns
without writing. If a syscall export cannot be made writable, `InitSyscalls`
advances to the next syscall record. If either `DisableCHPE` trampoline or
target-detour region cannot be made writable, `DisableCHPE` returns before the
corresponding byte writes.

No syscall-data layout, hook bytes, jump table routing, FFS/ARM64EC routing,
CHPE disabling policy, restore call, or instruction-cache flush call was
changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-119.py
bash docs/plan/check-srev-119.sh
```

Runtime/build gate still required:

- Windows x86/x64/ARM64 low-level build for `init.c`.
- Normal sandbox process startup with syscall hooks enabled and disabled.
- ARM64EC and CHPE-related startup where available.
- Failure-injection or instrumentation proving no write occurs after a failed
  writable-protection transition.
- Driver Verifier / loader-lock observation during early process initialization.
