# SREV-200: FileServer OpenBoxFile Path Gate

Stage: schema -> boundary -> action -> verify

Input artifact: `Sandboxie/core/svc/fileserver.h` and
`Sandboxie/core/svc/fileserver.cpp`

Output artifact: `FileServer::OpenBoxFile` stops before `NtCreateFile` when
the caller-supplied path fails the sandbox path gate.

Owner: `Sandboxie/core/svc/fileserver.h` / `Sandboxie/core/svc/fileserver.cpp`

Acceptance gate: `docs/plan/check-srev-200.py` plus
`docs/plan/check-srev-200.sh`.

## Data

`FileServer` is the `PipeServer` target for selected file and registry service
operations. The relevant crossing is:

```text
sandboxed process wire request
  -> FileServer::SetAttributes / SetShortName
  -> FileServer::OpenBoxFile
  -> CheckBoxFilePath
  -> NtCreateFile
```

Local evidence before this entry:

- `OpenBoxFile` called `CheckBoxFilePath(idProcess, request_path, L"\\")`.
- If that path gate failed, the code executed `SHORT_REPLY(status);` without
  returning from the `NTSTATUS` function.
- Execution then continued through `RtlInitUnicodeString`,
  `InitializeObjectAttributes`, and `NtCreateFile` using the original
  caller-supplied path.

## Official API Shape

`NtCreateFile` creates or opens the object named by `OBJECT_ATTRIBUTES` and the
requested access mask:

https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile

`InitializeObjectAttributes` initializes the object-name structure that handle
opening routines use:

https://learn.microsoft.com/en-us/windows/win32/api/ntdef/nf-ntdef-initializeobjectattributes

`RtlInitUnicodeString` initializes a counted `UNICODE_STRING` from a
null-terminated source string:

https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring

## Boundary

The boundary is the service broker crossing:

```text
untrusted sandboxed request path
  -> FileServer wire validation
  -> sandbox-root membership gate
  -> privileged service NtCreateFile
```

`FileServer::OpenBoxFile` owns the final gate before the privileged service
opens a path on behalf of a sandboxed process. A failed sandbox-root membership
check must be a terminal transition; it is not a reply-construction event inside
this helper.

## Topology

```text
SetAttributes / SetShortName
  -> validated counted WCHAR wire path
  -> OpenBoxFile
     -> CheckBoxFilePath
        -> SbieApi_QueryProcessPath sandbox file root
        -> prefix membership check
     -> return denied status on gate failure
     -> NtCreateFile only after gate success
```

## Logic

`SHORT_REPLY(status)` is legal only in a handler that returns `MSG_HEADER *`.
`OpenBoxFile` returns `NTSTATUS`; using `SHORT_REPLY(status)` there neither
returns nor proves a reply object is consumed by the caller.

The fix is the shortest legal transition:

```text
if (!NT_SUCCESS(status))
    return status;
```

This SREV does not change desired access, share mode, create options, wire
string validation, or the broader file-server policy. It only makes the existing
sandbox path gate terminal before the broker opens the file.

## Verification

Linux source gates prove:

- `OpenBoxFile` calls `CheckBoxFilePath` before `RtlInitUnicodeString` and
  `NtCreateFile`;
- the failure branch returns `status`;
- stale `SHORT_REPLY(status);` no longer appears inside `OpenBoxFile`;
- `SetAttributes` and `SetShortName` still call `OpenBoxFile` and convert its
  `NTSTATUS` to their own `SHORT_REPLY(status)`.

Runtime gate:

- Windows service build.
- Malformed or outside-sandbox path smoke for `MSGID_FILE_SET_ATTRIBUTES` and
  `MSGID_FILE_SET_SHORT_NAME`, proving the broker returns denial without opening
  the requested host path.
