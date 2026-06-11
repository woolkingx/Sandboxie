# SREV-180: Syscall32 Shadow Table Candidate Read Boundary

## Data

`Sandboxie/core/drv/syscall_32.c` owns the 32-bit syscall service-table
discovery fallback. `GetShadowTableAddress` scans the first 1024 bytes of
`KeAddSystemServiceTable`, treats each byte position as a possible
`PSYSTEM_SERVICE_TABLE` pointer, excludes `KeServiceDescriptorTable`, and
compares the candidate contents with `KeServiceDescriptorTable`.

Before this SREV, the scanner used `MmIsAddressValid(pTable)` as the only
readability gate before calling `memcmp(pTable, &KeServiceDescriptorTable,
sizeof(SYSTEM_SERVICE_TABLE))`.

## Official Shape

Microsoft documents `MmIsAddressValid` as checking whether a page fault would
occur for a read or write operation at a given virtual address, but the page
also says: "We do not recommend using this function." Its parameter text
requires the caller to ensure the address cannot be paged out or deleted for
the duration of the call. The remarks say: "Even if MmIsAddressValid returns TRUE",
accessing the address can still cause page faults unless the memory is locked
down or valid nonpaged pool.

Microsoft's driver exception-handling guidance says a driver "must handle raised exceptions"
and that an unhandled exception causes the system to bug check. The same
guidance says that if an operation might cause an exception, the driver should
enclose the operation in a `try/except` block. Microsoft's structured
exception handler syntax documents `__try` / `__except` as the frame-based
exception handler form.

Microsoft documents `MmGetSystemRoutineAddress` as resolving exported kernel or
HAL routines and returning `NULL` when a routine is not available. This file
uses that official resolver for other syscall32 helper routine probes, but
`KeServiceDescriptorTableShadow` discovery remains a private scanner fallback
with a Windows runtime gate.

```text
https://learn.microsoft.com/en-gb/windows-hardware/drivers/ddi/ntddk/nf-ntddk-mmisaddressvalid
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/handling-exceptions
https://learn.microsoft.com/en-us/windows/win32/debug/exception-handler-syntax
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmgetsystemroutineaddress
```

## Schema

Local schema:

```text
docs/plan/srev-180-syscall32-shadow-table-candidate-read-boundary.schema.json
```

The syscall32 shadow-table candidate read contract is:

```text
GetShadowTableAddress owns the 32-bit private shadow service-table fallback scanner
the scanner treats bytes in KeAddSystemServiceTable as untrusted candidate table pointers until locally validated
MmIsAddressValid is only a preliminary nonpaged-address check and is not sufficient proof for the following structure read
the candidate SYSTEM_SERVICE_TABLE comparison must be inside a structured exception boundary
the scanner must reject NULL candidates and KeServiceDescriptorTable itself before comparing contents
the helper preserves the existing 1024-byte scan window and the same-table-content predicate
this SREV does not change service-table offsets, syscall indices, process-flag offsets, or syscall dispatch
```

## Topology

Fallback discovery path:

```text
Syscall_GetServiceTable
  -> version offset guess for ShadowTable
  -> if missing or first entry mismatch, call GetShadowTableAddress
  -> scan KeAddSystemServiceTable byte window
  -> candidate pointer from private instruction bytes
  -> Syscall_IsShadowTableCandidate
       -> reject NULL and MasterTable identity
       -> MmIsAddressValid precheck
       -> guarded memcmp against KeServiceDescriptorTable
  -> return shadow table candidate or fail closed with MSG_1113 TABLE
```

## Logic Risk

The old predicate collapsed two different claims:

```text
page currently appears valid
the whole SYSTEM_SERVICE_TABLE candidate can be read safely right now
```

Microsoft's `MmIsAddressValid` documentation explicitly refuses that second
claim. In this private scanner, a false-positive candidate pointer derived from
instruction bytes could make `memcmp` dereference a bad or unstable structure
range. In kernel mode, that is the kind of access fault that can become a
bugcheck if it is not handled locally.

## Fix

`syscall_32.c` now has `Syscall_IsShadowTableCandidate`, a local helper that
keeps the previous candidate identity and content predicate but moves the
candidate structure comparison behind `__try` / `__except`. `MmIsAddressValid`
remains only as a preliminary precheck inside the guarded block.

No 32-bit service-table offsets, scan window size, process flag offset logic,
syscall index extraction, or syscall dispatch behavior changed.

## Acceptance Gate

`docs/plan/check-srev-180.py` validates the draft-07 schema, official
references, syscall32 source shape, guarded candidate comparison, removal of
the old direct `MmIsAddressValid || memcmp` predicate, unchanged fallback
scan window, and ledger fragment. `docs/plan/check-srev-180.sh` is the matrix
wrapper.

Runtime gate: Windows x86/32-bit-supported build and runtime matrix covering
service-table discovery fallback, Driver Verifier, HVCI/Core Isolation where
applicable, and ordinary NT plus win32k syscall dispatch smoke. Linux source
checks prove only the local source contract.
