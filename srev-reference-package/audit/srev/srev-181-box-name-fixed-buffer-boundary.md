# SREV-181: Box Name Fixed Buffer Boundary

## Data

`Sandboxie/core/drv/box.h` defines `BOX.name` as a fixed
`WCHAR name[BOXNAME_COUNT]` buffer and documents a sandbox identity as the box
name, user SID, and Terminal Services session. `Sandboxie/core/drv/box.c`
owns allocation of that identity through `Box_Alloc`, `Box_Create`,
`Box_CreateEx`, and `Box_Clone`.

Before this SREV, `Box_Alloc` copied its caller-supplied `boxname` into
`BOX.name` with `wcscpy`. Some callers already validate user-mode box names
through `Api_CopyBoxNameFromUser`, but `Box_Alloc` itself did not enforce the
`Box_IsValidName` contract before writing into the fixed owner buffer.

## Official Shape

Microsoft documents `RtlStringCchCopyW` as copying a null-terminated source
string into a destination buffer of a specified character length. It returns
`STATUS_SUCCESS` only when the source was copied without truncation and the
result is null-terminated. The same documentation says
`RtlStringCchCopyW` / `RtlStringCchCopyA` should be used instead of `wcscpy`,
and that the destination size is provided to ensure the operation does not
write past the end of the buffer.

Microsoft documents `RtlStringCchLengthW` / `RtlStringCchLengthA` as bounded
string-length helpers. The local owner already has a stricter semantic length
predicate in `Box_IsValidName`, so the repair keeps that project-level name
schema and uses the official bounded copy for the fixed buffer write.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcchcopyw
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcchlengtha
```

## Schema

Local schema:

```text
docs/plan/srev-181-box-name-fixed-buffer-boundary.schema.json
```

The box-name fixed-buffer contract is:

```text
box.c owns writes into BOX.name
BOX.name has exactly BOXNAME_COUNT WCHAR slots
Box_IsValidName is the local semantic schema for box identity names
Box_Alloc must reject NULL or invalid box names before allocating owner state or writing BOX.name
Box_Alloc must copy into BOX.name with a bounded API that receives BOXNAME_COUNT
Box_Alloc must fail closed and free any allocated BOX if the bounded copy fails
caller-side validation such as Api_CopyBoxNameFromUser is useful but is not the owner boundary
this SREV does not change valid box-name characters, enabled-box policy, SID/session ownership, path expansion, or process forcing
```

## Topology

Legal flow:

```text
caller boxname
  -> Box_Alloc owner boundary
  -> Box_IsValidName semantic gate
  -> allocate BOX
  -> RtlStringCchCopyW(BOX.name, BOXNAME_COUNT, boxname)
  -> name_len derives from copied owner buffer
  -> Box_InitKeys stores SID/session identity
  -> Box_InitPaths builds file/key/ipc roots
```

The box identity owner is `box.c`; API/config/process-force callers may perform
earlier validation, but they cannot be the final proof for a fixed owner buffer.

## Logic Risk

`BOX.name` is not just display text. It participates in box identity, config
lookup, process forcing, logging, service broker calls, and path/root expansion.
Letting a caller-supplied string reach `wcscpy` means the safety of a fixed
identity buffer depends on every current and future caller preserving the
contract. That is the wrong topology: the owner of the fixed buffer must enforce
the schema at the write boundary.

## Fix

Box_Alloc now rejects `NULL` or invalid box names before allocation, logs
`STATUS_INVALID_PARAMETER`, and uses `RtlStringCchCopyW(box->name,
BOXNAME_COUNT, boxname)` for the owner-buffer write. If the bounded copy fails,
it logs the returned status, frees the partially allocated `BOX`, and fails
closed.

No valid box-name character set, `Api_CopyBoxNameFromUser`, enabled-box policy,
SID/session storage, path expansion, force-process discovery, or service broker
wire shape changed.

## Acceptance Gate

`docs/plan/check-srev-181.py` validates the draft-07 schema, official
references, `BOX.name` fixed-buffer evidence, `Box_IsValidName` owner gate,
bounded `RtlStringCchCopyW` copy with `BOXNAME_COUNT`, failure cleanup, removal
of the direct `wcscpy(box->name, boxname)` write, representative caller
evidence, and ledger fragment. `docs/plan/check-srev-181.sh` is the matrix
wrapper.

Runtime gate: Windows driver build plus box creation smoke for a valid box name,
invalid/oversized user-mode box-name rejection through API paths, invalid
configuration section rejection for force-process discovery, and normal SID,
session, file/key/ipc root creation for existing valid boxes.
