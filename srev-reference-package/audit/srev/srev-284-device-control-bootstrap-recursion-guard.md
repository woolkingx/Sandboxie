# SREV-284: Device-Control Bootstrap Recursion Guard

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file_pipe.c`, `Sandboxie/core/dll/sbieapi.c`, SREV-281, SREV-139, Microsoft `ZwDeviceIoControlFile` and IOCTL documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_NtDeviceIoControlFile` bootstrap guard before native pointer publication |
| Acceptance gate | Targeted checker validates official references, bootstrap guard predicate, SbieApi bypass adjacency, network-filter adjacency, stale source wording removal, and ledger fragment |

## Data

`File_NtDeviceIoControlFile` has two separate local responsibilities:

```text
TCP/NSI network-parameter deny logic
native NtDeviceIoControlFile pass-through
```

Before pass-through, it checks whether `__sys_NtDeviceIoControlFile` has already
been published:

```text
if (!__sys_NtDeviceIoControlFile)
    return STATUS_BAD_INITIAL_PC;
```

`sbieapi.c` shows why that state matters. Once `__sys_NtDeviceIoControlFile` is
available, `SbieApi_Ioctl` bypasses the hooked export and calls the native
pointer directly. Before that, the same helper falls back to
`NtDeviceIoControlFile`, which may be the hook being installed.

## Official Shape

Microsoft documents `ZwDeviceIoControlFile` as sending a control code directly
to a specified device driver. The `IoControlCode` selects the operation and the
required input/output buffer shape. Microsoft also notes that user-mode callers
use the `NtDeviceIoControlFile` name.

Microsoft documents IOCTLs as the control-code communication layer between
applications and drivers or between drivers.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwdeviceiocontrolfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/introduction-to-i-o-control-codes`

## Schema

Local schema:

```text
docs/plan/srev-284-device-control-bootstrap-recursion-guard.schema.json
```

Contract id:

```text
DEVICE_CONTROL_BOOTSTRAP_RECURSION_GUARD
```

## Boundary

```text
File_NtDeviceIoControlFile hook
  -> local TCP/NSI policy
  -> native pointer publication gate
  -> __sys_NtDeviceIoControlFile pass-through
```

The bootstrap guard owns only the pre-publication state where calling the hooked
export again can re-enter the same hook through Sandboxie's own monitor/API
path. SREV-281 owns the user-visible BlockNetParam registration and TCP/NSI
policy. SREV-139 owns the driver-side syscall-level `NtDeviceIoControlFile`
deny completion contract.

## Topology

```text
normal installed state:
  File_NtDeviceIoControlFile
    -> __sys_NtDeviceIoControlFile

SbieApi after native pointer publication:
  SbieApi_Ioctl
    -> __sys_NtDeviceIoControlFile

bootstrap pre-publication state:
  monitor/API path
    -> SbieApi_Ioctl
    -> NtDeviceIoControlFile export
    -> File_NtDeviceIoControlFile
    -> STATUS_BAD_INITIAL_PC sentinel
```

## Logic Risk

The old source comment named the failure mode with informal wording but not the
owner boundary. A future edit could remove the guard as log-noise cleanup or
replace the sentinel with native pass-through before the native pointer is
available. That would blur bootstrap state, monitor logging, and regular
device-control policy. The guard must remain a narrow pre-publication sentinel;
it must not be treated as TCP/NSI deny policy or a general device-control
failure result.

## Fix

Comment-only source clarification. The source now names SREV-284 and states
that the guard applies only while `__sys_NtDeviceIoControlFile` is unpublished,
so Sandboxie's own monitor/API path does not re-enter the partially installed
hook. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-284.py` validates the draft-07 schema, official
references, source guard predicate and sentinel, native pass-through
preservation, SbieApi bypass adjacency, SREV-281/SREV-139 adjacency, stale
source wording removal, and ledger fragment.

Runtime gate: Windows hook-bootstrap trace proving monitor/API traffic before
native pointer publication observes the sentinel without recursive hook entry,
plus normal post-install `NtDeviceIoControlFile` pass-through and SREV-281
TCP/NSI deny behavior.
