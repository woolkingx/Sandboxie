# SREV-125 File Copy Junction Handle State

## Data

Owner file:

```text
Sandboxie/core/dll/file_copy.c
```

Reviewed nodes:

```text
File_MigrateJunction
TruePath
CopyPath
TrueHandle
CopyHandle
open_info
FILE_NETWORK_OPEN_INFORMATION
REPARSE_DATA_BUFFER
FSCTL_GET_REPARSE_POINT
FSCTL_SET_REPARSE_POINT
NtCreateFile
NtQueryInformationFile
NtFsControlFile
NtClose
File_SetAttributes
pSecurityDescriptor
```

## Schema

`FILE_COPY_JUNCTION_HANDLE_STATE` defines these local contracts:

- `File_MigrateJunction` opens the source reparse point before querying source
  metadata or reparse data.
- `FILE_NETWORK_OPEN_INFORMATION` is used only after
  `NtQueryInformationFile(FileNetworkOpenInformation)` succeeds.
- Source reparse data is used only after `FSCTL_GET_REPARSE_POINT` succeeds.
- Every local failure after `TrueHandle` opens closes `TrueHandle` before
  returning.
- Destination reparse data is set only after destination `NtCreateFile`
  succeeds and initializes `CopyHandle`.
- Destination create failure frees the copied security descriptor when one
  exists and returns before `FSCTL_SET_REPARSE_POINT`.
- Reparse data shape, ACL copy policy, destination create options, and
  attribute-copy behavior are unchanged.

## Topology

```text
File_MigrateJunction
  -> NtCreateFile(TruePath, FILE_OPEN_REPARSE_POINT)
  -> NtQueryInformationFile(TrueHandle, FileNetworkOpenInformation)
  -> NtFsControlFile(TrueHandle, FSCTL_GET_REPARSE_POINT)
  -> optional NtQuerySecurityObject / File_AddCurrentUserToSD
  -> NtCreateFile(CopyPath, FILE_CREATE | FILE_OPEN_REPARSE_POINT)
  -> NtFsControlFile(CopyHandle, FSCTL_SET_REPARSE_POINT)
  -> File_SetAttributes(CopyHandle, open_info)
  -> close handles and free copied SD
```

Failure topology:

```text
source query failure -> NtClose(TrueHandle) -> return
source get-reparse failure -> NtClose(TrueHandle) -> return
destination create failure -> NtClose(TrueHandle) -> optional Dll_Free(SD) -> return
```

## Logic Risk

The old junction-copy path did not check the source metadata query before later
using `open_info` to copy timestamps and attributes. It also returned directly
after `FSCTL_GET_REPARSE_POINT` failure without closing `TrueHandle`. Most
critically, destination `NtCreateFile` failure closed the source handle and freed
the security descriptor but did not return, so execution fell through into
`FSCTL_SET_REPARSE_POINT` with an uninitialized or invalid `CopyHandle`.

The correct local repair is to make each native handle-producing or
state-producing call gate the next edge. This does not change junction policy,
reparse-buffer layout, source open flags, destination create flags, security
descriptor copying, or attribute propagation.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryinformationfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntfscontrolfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-set-reparse-point
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/a4942f57-dfa2-4852-a971-db1b8ad37150
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose

## Fix

`File_MigrateJunction` now checks `NtQueryInformationFile` before reparse data
work and closes `TrueHandle` on query failure. It also closes `TrueHandle`
before returning on `FSCTL_GET_REPARSE_POINT` failure. Destination
`NtCreateFile` failure now closes `TrueHandle`, frees `pSecurityDescriptor` when
one exists, and returns immediately before any `FSCTL_SET_REPARSE_POINT` call can
use `CopyHandle`.

No source open access, `FILE_OPEN_REPARSE_POINT` use, reparse buffer size,
`FSCTL_SET_REPARSE_POINT` input length, copied ACL policy, `File_SetAttributes`
call, or final successful cleanup path changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-125.py
bash docs/plan/check-srev-125.sh
```

Runtime/build gate still required:

- Windows build for `file_copy.c`.
- Junction migration positive smoke proving unchanged source reparse open,
  `FSCTL_GET_REPARSE_POINT`, destination create, `FSCTL_SET_REPARSE_POINT`, and
  attribute copy.
- Failure injection for source `NtQueryInformationFile` proving `TrueHandle` is
  closed and `open_info` is not consumed.
- Failure injection for `FSCTL_GET_REPARSE_POINT` proving `TrueHandle` is closed.
- Failure injection for destination `NtCreateFile` proving no
  `FSCTL_SET_REPARSE_POINT` call occurs with an invalid `CopyHandle`, and copied
  security descriptor storage is freed when allocated.
