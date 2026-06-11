# SREV-101: Syscall Disabled Skip And Procmon Guard

## Data

`Sandboxie/core/drv/syscall.c` owns the driver-side native syscall table. During
initialization it enumerates `Zw*` exports from NTDLL, derives syscall indexes
and kernel addresses, and stores `SYSCALL_ENTRY` records for later dispatch.

The uncovered comment hits in this file were:

```text
YieldExecution inactive compatibility skip comment
MapViewOfSection inactive compatibility skip comment
QuerySystemInformation class 0xb9 Procmon stack guard comment
```

The first two are commented-out skip branches. They do not currently change
hook behavior. The third is an active support predicate wired by
`Syscall_Set3("QuerySystemInformation", Syscall_QuerySystemInfo_SupportProcmonStack)`.

## Official Shape

Microsoft documents native operating system services as kernel-mode routines
whose names begin with `Nt` or `Zw`; user-mode applications access them through
system calls. Microsoft documents that, for user-mode callers, `Nt` and `Zw`
versions behave identically and treat parameters as untrusted user-mode values.

Microsoft documents `ZwMapViewOfSection` as mapping a view of a section and
links it to the broader section-object model. Microsoft also documents memory
sections as `ZwCreateSection` / `ZwOpenSection` / `ZwMapViewOfSection` /
`ZwUnmapViewOfSection` topology. That gives the API shape for the
`MapViewOfSection` hook name, but it does not prove Chrome `wow_helper`
compatibility policy.

Microsoft documents `NtQuerySystemInformation` as a native API that may be
altered or unavailable in future Windows versions. The public page documents
some `SYSTEM_INFORMATION_CLASS` values including speculation-control classes,
but the local `0xb9` guard remains a private runtime-version-specific value in
Sandboxie's source. That boundary matters: this SREV can document the local
guard, not promote `0xb9` into a stable public contract.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-nt-and-zw-versions-of-the-native-system-services-routines
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwmapviewofsection
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/managing-memory-sections
https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation
https://learn.microsoft.com/en-us/windows/win32/sysinfo/zwquerysysteminformation
```

## Schema

Local schema:

```text
docs/plan/srev-101-syscall-disabled-skip-and-procmon-guard.schema.json
```

The syscall disabled-skip and Procmon guard contract is:

```text
Syscall_Init enumerates NTDLL Zw exports and builds the Sandboxie syscall table
YieldExecution and MapViewOfSection compatibility skip branches are intentionally inactive comments
the inactive skip branches must not be described as active third-party workaround policy
MapViewOfSection hook policy must not be changed from stale Chrome wow_helper comments alone
QuerySystemInformation is registered through Syscall_Set3 with Syscall_QuerySystemInfo_SupportProcmonStack
SystemInformationClass 0xb9 is a private runtime guard value and is not a public SYSTEM_INFORMATION_CLASS contract
NtQuerySystemInformation is a variable native API surface and must be treated as runtime-version gated
this SREV does not change syscall hook registration, skip behavior, or QuerySystemInformation return policy
```

## Topology

Initialization path:

```text
Dll_Load(NTDLL)
  -> Dll_GetNextProc(..., "Zw", ...)
  -> Syscall_GetIndexFromNtdll
  -> Syscall_GetKernelAddr
  -> List_Insert_After(Syscall_List, SYSCALL_ENTRY)
  -> Syscall_Table[index] = entry
```

Hook/guard path:

```text
Syscall_Set3("QuerySystemInformation", Syscall_QuerySystemInfo_SupportProcmonStack)
  -> Syscall_Api_Invoke
  -> handler checks user_args[0]
  -> class 0xb9 returns FALSE for Procmon stack support
```

Inactive compatibility notes:

```text
YieldExecution skip branch is commented out
MapViewOfSection skip branch is commented out
normal syscall table inclusion still proceeds if the syscall is otherwise valid
```

## Logic Risk

The old `$Workaround$ - 3rd party fix` suffix made inactive comments look like
active policy. That is risky in both directions: a reviewer could mistakenly
believe Sandboxie still skips those syscalls, or could re-enable the branches
without runtime evidence.

For `QuerySystemInformation`, the old comment used an outcome word rather than
the boundary. The real boundary is that `0xb9` is a private, runtime-versioned
class value observed by local code and not a public Microsoft contract.

## Fix

Comment-only source clarification:

```text
YieldExecution and MapViewOfSection notes now say the skip branches are historical and intentionally inactive.
The Procmon stack guard now says class 0xb9 can destabilize x64 context rather than presenting it as a general crash claim.
```

No syscall hook registration, skip behavior, handler return value, or runtime
behavior was changed.

## Acceptance Gate

`docs/plan/check-srev-101.py` validates the draft-07 schema, official
references, NTDLL `Zw*` enumeration topology, inactive YieldExecution and
MapViewOfSection branches, `Syscall_Set3("QuerySystemInformation", ...)`
wiring, class `0xb9` guard behavior, stale `$Workaround$ and crash wording
removal from `syscall.c`, and ledger entry. `docs/plan/check-srev-101.sh` is
the matrix wrapper.

Runtime gate: Windows x86/x64 syscall-hook matrix with McAfee ICD-10607,
Chrome `wow_helper`, `NtMapViewOfSection`, `NtYieldExecution`, Procmon stack
capture, `NtQuerySystemInformation(0xb9)`, HVCI on/off, and Driver Verifier
observation for syscall table and hook dispatch stability.
