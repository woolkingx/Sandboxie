# SREV-020 GetFileName Type Output ABI Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents `METHOD_NEITHER` style user buffers as original user-space
virtual addresses passed to the driver. The driver must validate the user
buffer range with probing routines, access the buffer in the caller context or
lock/map it itself, and wrap both probing and subsequent access in structured
exception handling.

`ProbeForWrite` is documented as historical compatibility only; Microsoft
recommends `ProbeForRead` for validation because robust drivers must still be
prepared for protection changes after probing. The key rule remains: every
user-buffer output needs a known byte length and exception-protected access.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-neither-buffered-nor-direct-i-o
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/handling-exceptions

## Local Shape

The driver-side `API_GET_FILE_NAME_ARGS` declares `type_buf` as a `WCHAR *`.
The public DLL header exposed the fourth `SbieApi_GetFileName` argument as
`ULONG *ObjType`.

Before this patch, the driver treated a non-NULL `type_buf` as a writable
wide-character string buffer and copied `objectType->Name` plus a terminator
without any caller-provided type-buffer length. A caller following the public
`ULONG *` declaration could therefore provide a 4-byte buffer for a driver
write of an object-type string such as `File`, `Device`, or `ALPC Port`.

Current in-tree callers pass `NULL` for the fourth argument.

## Local Risk

The ABI exposes two incompatible shapes for the same pointer:

- public caller shape: `ULONG *`
- driver writer shape: unbounded `WCHAR *` string output

The official user-buffer posture does not permit an output string without a
byte length. Probing `objectType->Name.Length + sizeof(WCHAR)` only proves that
the driver can touch that many bytes at the supplied address; it does not prove
that the caller allocated that shape according to the public ABI.

## Patch Boundary

Do not invent a new ABI inside the old slot. The fourth argument is treated as
reserved unless a future bounded API adds both a type buffer pointer and a type
buffer byte length.

The driver now rejects non-NULL `type_buf` with `STATUS_INVALID_PARAMETER`
before any type-name write. Existing in-tree callers that pass `NULL` keep the
current file-name behavior.

## Acceptance Gate

- No driver write to `type_buf` remains.
- A non-NULL fourth argument fails closed with `STATUS_INVALID_PARAMETER`.
- `SbieApi_GetFileName(..., NULL)` call sites remain valid.
- Runtime gate remains open: a 4-byte non-NULL fourth argument must fail
  without writing past the buffer; existing name queries must still work.
