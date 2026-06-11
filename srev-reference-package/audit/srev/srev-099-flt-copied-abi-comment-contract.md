# SREV-099: FLT Copied ABI Comment Contract

## Data

`Sandboxie/core/drv/my_fltkernel.h` is a local copy/subset of WDK
`fltKernel.h`. The header itself names the data reason: Sandboxie cannot use
the DDK `fltKernel.h` directly because that header does not compile when
`_WIN32_WINNT < NTDDI_VISTA`, which would prevent building a driver that still
runs under XP.

The comment-admitted lines were not behavioral warnings. They were copied ABI
descriptions that used the word "broken" to describe ordinary structure
partitioning:

```text
FLT_PARAMETERS.FileSystemControl -> Common / Neither / Buffered / Direct
FLT_PARAMETERS.DeviceIoControl   -> Common / Neither / Buffered / Direct / FastIo
FLT_FILE_NAME_OPTIONS            -> format bits / query-method bits / unused bits / flags
```

Local consumers include `Sandboxie/core/drv/file_flt.c`, which reads
`Iopb->Parameters`, calls `FltGetFileNameInformation`, and uses
`FLT_FILE_NAME_NORMALIZED | FLT_FILE_NAME_QUERY_DEFAULT` for normalized target
path queries.

## Official Shape

Microsoft documents `FLT_PARAMETERS` as the minifilter request-specific
parameter union associated with an I/O operation. Its documented
`FileSystemControl` member contains method-specific arms named `Common`,
`Neither`, `Buffered`, and `Direct`. Its documented `DeviceIoControl` member
contains `Common`, `Neither`, `Buffered`, `Direct`, and `FastIo`.

Microsoft documents `FLT_FILE_NAME_OPTIONS` as a `ULONG` value that specifies
the file-name format, query method, and flags for a file-name information
query. The official partition is:

```text
bits 0..7   -> file name format
bits 8..15  -> query method
bits 16..23 -> currently unused
bits 24..31 -> flags
```

Microsoft documents `FltGetFileNameInformation` as returning name information
for the file or directory described by `CallbackData`, in the requested format.
The same page documents query method flags including
`FLT_FILE_NAME_QUERY_DEFAULT`, `FLT_FILE_NAME_QUERY_CACHE_ONLY`,
`FLT_FILE_NAME_QUERY_FILESYSTEM_ONLY`, and
`FLT_FILE_NAME_QUERY_ALWAYS_ALLOW_CACHE_LOOKUP`.

Microsoft's preoperation user-buffer guidance also uses
`CallbackData->Iopb->Parameters` as the legal minifilter callback-data path for
operation-specific buffer metadata.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fltkernel/ns-fltkernel-_flt_parameters
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fltkernel/nf-fltkernel-fltgetfilenameinformation
https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/flt-file-name-options
https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/accessing-user-buffers-in-a-preoperation-callback-routine
```

## Schema

Local schema:

```text
docs/plan/srev-099-flt-copied-abi-comment-contract.schema.json
```

The copied FLT ABI comment contract is:

```text
my_fltkernel.h is a local copied fltKernel.h subset kept for _WIN32_WINNT below Vista / XP driver build compatibility
this SREV does not change the copied FLT ABI layout or numeric constants
FLT_PARAMETERS contains method-specific FileSystemControl and DeviceIoControl union arms
the FileSystemControl method arms are Common, Neither, Buffered, and Direct
the DeviceIoControl method arms are Common, Neither, Buffered, Direct, and FastIo
FLT_FILE_NAME_OPTIONS is a ULONG partitioned into name format bits, query method bits, unused bits, and flags
FLT_FILE_NAME_NORMALIZED and FLT_FILE_NAME_QUERY_DEFAULT remain the local normalized-name query contract
comment wording must not describe official partitioned ABI fields as broken
file_flt.c remains the local Filter Manager consumer for Iopb->Parameters and FltGetFileNameInformation
```

## Topology

```text
WDK Filter Manager ABI
  -> local copied my_fltkernel.h subset for legacy XP-compatible builds
  -> file_flt.c minifilter callbacks
  -> CallbackData->Iopb
  -> Iopb->Parameters operation-specific union
  -> FltGetFileNameInformation(... FLT_FILE_NAME_NORMALIZED | FLT_FILE_NAME_QUERY_DEFAULT ...)
```

The ownership boundary is important: `my_fltkernel.h` mirrors an external ABI.
This SREV can clarify misleading local comments, but it must not reshape the
copied structures or numeric constants without a WDK/Windows build matrix.

## Logic Risk

The risk was review drift, not a discovered runtime bug. The old comments made
normal ABI partitioning look like a self-admitted broken state. A reviewer could
then "fix" the wrong thing by changing copied WDK layout, which is exactly the
wrong boundary: the legal shape is the external Filter Manager ABI.

The narrow fix is to replace the misleading wording with neutral ABI wording:
method-specific parameters are "split" into union arms, and
`FLT_FILE_NAME_OPTIONS` is "partitioned" into bit ranges.

## Fix

Comment-only source clarification:

```text
broken out into -> split into
broken down into -> partitioned into
```

No ABI layout, numeric constant, callback registration, or runtime behavior was
changed.

## Acceptance Gate

`docs/plan/check-srev-099.py` validates the draft-07 schema, official
references, the legacy copied-header reason, `FLT_PARAMETERS` union arms,
`FLT_FILE_NAME_OPTIONS` masks and values, stale `broken out into` /
`broken down into` wording removal, local `file_flt.c` and `process.c`
consumer shape, and ledger entry. `docs/plan/check-srev-099.sh` is the matrix
wrapper.

Runtime gate: Windows/WDK matrix with XP-compatible build settings, Vista+
minifilter load, `IRP_MJ_SET_INFORMATION` rename/link callbacks,
`FltGetFileNameInformation` normalized-name queries, and Driver Verifier
observation for copied `FLT_PARAMETERS` layout compatibility.
