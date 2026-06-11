# SREV-331: File Filter Spooler Probe Exceptions

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/drv/file_flt.c`, Microsoft print spooler, port monitor, file-name namespace, communications resource, and `CreateFile` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `file_flt.c` spoolsv impersonated write deny gate |
| Acceptance gate | Targeted checker validates official references, scoped spooler predicates, probe exceptions, stale hack wording removal, and ledger fragment |

## Data

`file_flt.c` blocks write creates from a system-account `spoolsv.exe` thread
when the spooler is impersonating a sandboxed user and
`AllowSpoolerPrintToFile` is not enabled. The deny branch excludes three
spooler compatibility probes before applying the sandbox write policy:

- target names that end in `:`;
- `tpwinprn-stat.txt`;
- `\pipe\spoolss`.

The first two exceptions had "stupid hack" comments. The code shape is more
specific than that wording: the exceptions are scoped to `spoolsv.exe`, generic
write create requests, a system-account process, a sandboxed owner process, and
the disabled `AllowSpoolerPrintToFile` policy branch.

## Official Shape

Microsoft documents the print spooler as the subsystem that accepts print data,
spools data to files when enabled, sends data to printer hardware, and hosts
optional vendor-supplied components.

Microsoft documents `Spoolsv.exe` as the spooler's API server. Print calls are
passed through the router to print providers, while print monitors provide the
communications path between the user-mode spooler and kernel-mode port drivers.
Port monitors commonly use `CreateFile`, `WriteFile`, `ReadFile`, and
`DeviceIoControl` to communicate with port drivers.

Microsoft documents Windows file-name rules with `:` as a reserved character in
ordinary file and directory names, while `CreateFile` can also open files,
streams, devices, mailslots, and pipes. Microsoft documents communications
resources such as COM and LPT ports as `CreateFile` targets.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/print/print-spooler-architecture`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/print/introduction-to-spooler-components`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/print/port-monitors`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file`
- `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilea`
- `https://learn.microsoft.com/en-us/windows/win32/devio/communications-resource-handles`

## Boundary

```text
spoolsv.exe system process
  -> impersonated sandboxed user token
  -> IRP_MJ_CREATE generic-write request
  -> file_flt.c print-to-file deny gate
  -> narrow spooler probe exceptions
  -> normal filesystem/device/pipe owner decides result
```

The sandbox owns the print-to-file deny decision. It does not own the native
parsing status for malformed path/device-name probes or private printer-driver
status probes. Those requests should fall through only while the spooler gate is
already proven by process name, system-account context, desired write access,
and sandboxed owner process.

## Topology

```text
spoolsv.exe + SBIE_FILE_GENERIC_WRITE
  -> target ends with ':'
  -> not denied by print-to-file branch
  -> filesystem/device-name parser owns invalid-name or device result

spoolsv.exe + SBIE_FILE_GENERIC_WRITE
  -> target contains tpwinprn-stat.txt
  -> not denied by print-to-file branch
  -> printer-driver status probe compatibility

spoolsv.exe + SBIE_FILE_GENERIC_WRITE
  -> target contains \pipe\spoolss
  -> not denied by print-to-file branch
  -> pipe/spooler owner handles the request
```

## Logic Risk

The old comments made the exceptions look arbitrary and broad. That is risky in
a security boundary: future edits might move the exceptions outside the spooler
gate, expand them to non-spooler processes, or replace native path/device-name
failure with sandbox `STATUS_ACCESS_DENIED`.

## Fix

Comment-only source clarification. The source now names SREV-331 and describes
the `:` suffix and `tpwinprn-stat.txt` branches as scoped spooler/port-monitor
probe exceptions. No predicate, access mask, process-name check, sandbox-owner
check, pipe exception, file policy call, or return status changed.

## Acceptance Gate

`docs/plan/check-srev-331.py` validates the draft-07 schema, official
references, `spoolsv.exe` / `SBIE_FILE_GENERIC_WRITE` / system-account /
sandbox-owner gates, the three existing exceptions, source comment ownership,
stale hack wording removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows print matrix with a sandboxed print-to-file denial,
allowed spooler work directory, `AllowSpoolerPrintToFile=y`, a printer/port
driver path ending in `:`, `tpwinprn-stat.txt`, `\pipe\spoolss`, and a negative
control proving non-spooler write creates do not inherit these exceptions.
