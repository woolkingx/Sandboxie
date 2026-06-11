# SREV-184 XP File Open Packet Offset Contract

## Data

Owner file:

```text
Sandboxie/core/drv/file_xp.c
```

Reviewed nodes:

```text
OPEN_PACKET
File_CreateMyContext
File_File_MyParseProc
File_Device_MyParseProc
File_Generic_MyParseProc
OBJ_PARSE_PROC_ARGS
OBJ_CALL_SYSTEM_PARSE_PROC
FIELD_OFFSET
ACCESS_STATE.OriginalDesiredAccess
IO_OPEN_TARGET_DIRECTORY
```

## Schema

`XP_FILE_OPEN_PACKET_OFFSET_CONTRACT` defines these local contracts:

- `file_xp.c` owns the 32-bit Windows XP/2003 file and device parse-procedure hook.
- `OPEN_PACKET` is a private local layout mirror used only by the XP parse-procedure path.
- `File_CreateMyContext` may read `CreateOptions`, `Options`, and `CreateDisposition` only after `Context->Type == IO_TYPE_OPEN_PACKET`.
- The expected 32-bit offsets are `CreateOptions == 0x20`, `Options == 0x30`, and `CreateDisposition == 0x34`.
- The offsets are compile-time gates through `FIELD_OFFSET`; changing the local `OPEN_PACKET` layout must fail the source gate.
- Vista and later use the minifilter route, so this XP parse hook must not claim Vista/7/8 context layout compatibility.
- This SREV does not change file/device parse-procedure routing, policy decisions, `IO_OPEN_TARGET_DIRECTORY` handling, font token handling, or minifilter behavior.
- Windows XP/2003 build and runtime proof are required.

## Topology

The XP-only path is:

```text
File_Init
  -> Driver_OsVersion < DRIVER_WINDOWS_VISTA
  -> File_Init_XpHook
  -> Obj_HookParseProc("File", File_File_MyParseProc)
  -> Obj_HookParseProc("Device", File_Device_MyParseProc)
  -> File_CreateMyContext
  -> File_Generic_MyParseProc
  -> OBJ_CALL_SYSTEM_PARSE_PROC
```

Vista and later use:

```text
File_Init -> File_Init_Filter -> file_flt.c -> File_Generic_MyParseProc
```

Therefore the legal `OPEN_PACKET` contract belongs only to the legacy 32-bit XP
hook. It is not a general file-open schema for newer Windows versions.

## Logic Risk

Before this SREV, the source comments named the private offsets `0x20`, `0x30`,
and `0x34`, but the source did not gate those offsets. A future field edit,
porting attempt, compiler packing change, or mistaken reuse outside the XP path
could silently change the private `OPEN_PACKET` layout and make
`File_CreateMyContext` copy the wrong create options into policy logic.

The same comment also suggested the old XP offset code "works" for Vista, 7,
and 8 after an eight-byte adjustment, but the local dispatch in `file.c` uses
`File_Init_XpHook` only when `Driver_OsVersion < DRIVER_WINDOWS_VISTA`. Keeping
that stale claim makes the boundary look wider than it is.

## Official Shape

Microsoft documents `FIELD_OFFSET` as the driver macro that returns the byte
offset of a named field in a known structure type. That is the correct local
tool for making this private layout assumption mechanical.

Microsoft documents `ACCESS_STATE` as the state of an access in progress and
names `OriginalDesiredAccess` as the original requested access rights. This
supports the local read from `AccessState->OriginalDesiredAccess`; it does not
legalize modifying `ACCESS_STATE` or deriving the private `OPEN_PACKET` layout
from public docs.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-field_offset
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_access_state

## Fix

`file_xp.c` now declares compile-time layout gates:

```text
FIELD_OFFSET(OPEN_PACKET, CreateOptions) == 0x20
FIELD_OFFSET(OPEN_PACKET, Options) == 0x30
FIELD_OFFSET(OPEN_PACKET, CreateDisposition) == 0x34
```

The stale Vista/7/8 comment in `File_CreateMyContext` now states the actual
owner boundary: this is a legacy XP/2003 parse-procedure path and Vista+ uses
the minifilter route.

No file policy, device-type filtering, token replacement, parse-procedure
dispatch, minifilter path, or `IO_OPEN_TARGET_DIRECTORY` exception behavior
changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-184.py
bash docs/plan/check-srev-184.sh
```

Runtime gate still required:

- Windows XP/2003 32-bit driver build with `XP_SUPPORT`.
- XP file and device parse-procedure hook install/unload smoke.
- File create/open/rename smoke proving `IO_OPEN_TARGET_DIRECTORY` handling is unchanged.
- Vista+ minifilter smoke proving this legacy file is not in the active route.
