# SREV-333: File Filter Kaspersky Swmon Sentinel

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/file_flt.c`, `Sandboxie/core/drv/syscall_open.c`, SREV-329, Microsoft `NtSetInformationThread`, APC, and WOW64 documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_CheckFileObject` Kaspersky `swmon_*_kl1` sentinel |
| Acceptance gate | Targeted checker validates official references, x64/pre-SbieDll gate, swmon name predicate, `STATUS_BAD_INITIAL_PC` sentinel topology, SREV-329 adjacency, stale hack/workaround wording removal, and ledger fragment |

## Data

`File_CheckFileObject` contains a Kaspersky 2014 compatibility gate. On x64,
before SbieDll is loaded, it checks file-object names whose last path component
starts with `swmon_` and whose suffix is `_kl1`. Matching objects return
`STATUS_BAD_INITIAL_PC`.

The old comment described the behavior as a hack/workaround. The actual local
shape is narrower:

- x64-only compile gate;
- process-local early stage: `!proc->sbiedll_loaded`;
- path predicate: backslash exists, underscore exists, suffix `_kl1`, component
  prefix `\swmon_`;
- sentinel status: `STATUS_BAD_INITIAL_PC`;
- adjacent consumer: `Syscall_OpenHandle` treats `STATUS_BAD_INITIAL_PC` as a
  non-canceling status in the restored-handle path.

## Official Shape

Microsoft documents `ZwSetInformationThread` / user-mode
`NtSetInformationThread` as receiving a thread handle, information class,
information pointer, and byte length, returning an NTSTATUS result.

Microsoft documents user-mode APCs as queued to threads and notes that
cross-process APC queuing is not recommended because address and execution
context can be wrong, including cross-architecture cases.

Microsoft documents WOW64 as the x86 emulator for running 32-bit applications
on 64-bit Windows. WOW64 interposes between the 32-bit `Ntdll.dll` and the
kernel and loads the x86 NTDLL at startup.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-zwsetinformationthread`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-queueuserapc`
- `https://learn.microsoft.com/en-us/windows/win32/winprog64/running-32-bit-applications`
- `https://learn.microsoft.com/en-us/windows/win32/winprog64/wow64-implementation-details`

## Boundary

```text
early x64 sandboxed process before SbieDll load
  -> file object open for Kaspersky swmon_*_kl1
  -> File_CheckFileObject name predicate
  -> STATUS_BAD_INITIAL_PC sentinel
  -> Syscall_OpenHandle non-canceling handling
  -> SbieDll can preserve NtSetInformationThread topology
```

`File_CheckFileObject` does not own the native `NtSetInformationThread`
operation. It owns only this early device/file-object access sentinel that keeps
the later SbieDll / SREV-329 `NtSetInformationThread` topology from being
patched before Sandboxie has finished loading.

## Topology

```text
File_CheckFileObject
  -> _WIN64
  -> !proc->sbiedll_loaded
  -> NameString last backslash + last underscore
  -> suffix _kl1 and component prefix \swmon_
  -> STATUS_BAD_INITIAL_PC
  -> Syscall_OpenHandle sentinel handling

SREV-329 adjacency
  -> SbieDll NtSetInformationThread pass-through guard
  -> Gui_ConnectToWindowStationAndDesktop change-notify-token path
```

## Logic Risk

The stale comments made the branch look like a broad third-party compatibility
hack. Future edits could expand the name predicate, run it after SbieDll is
loaded, or remove it as cosmetic cleanup without proving the
`NtSetInformationThread` change-notify-token path under Kaspersky/WOW64
runtime conditions.

## Fix

Comment-only source clarification. The source now names SREV-333, the
Kaspersky/WOW64/APC/`NtSetInformationThread` adjacency, and the narrow x64
pre-SbieDll-loaded `swmon_*_kl1` sentinel. No compile gate, load-stage gate,
name predicate, return status, or `Syscall_OpenHandle` handling changed.

## Acceptance Gate

`docs/plan/check-srev-333.py` validates the draft-07 schema, official
references, source comment ownership, x64 and `!proc->sbiedll_loaded` gates,
`swmon_` / `_kl1` matching, `STATUS_BAD_INITIAL_PC`, `Syscall_OpenHandle`
sentinel handling, SREV-329 adjacency, stale hack/workaround wording removal,
combined ledger entry, and split ledger fragment.

Runtime gate: Windows Kaspersky/WOW64 matrix covering pre-SbieDll load,
post-SbieDll load, matching and non-matching `swmon_*_kl1` names,
`Syscall_OpenHandle` non-canceling sentinel behavior, and SREV-329
`NtSetInformationThread` change-notify-token regression checks.
