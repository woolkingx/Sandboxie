# SREV-014 FSCTL_PIPE_WAIT Buffer Shape

Status: source-level spec before patch.

## Official Shape

MS-FSCC defines the `FSCTL_PIPE_WAIT` request as:

```text
Timeout          8 bytes
NameLength       4 bytes
TimeoutSpecified 1 byte
Padding          1 byte
Name             variable Unicode string
```

`NameLength` is the size in bytes of `Name`. `Name` must not include the
`\pipe\` prefix; for `\\server\pipe\pipename`, the request name is `pipename`.
`TimeoutSpecified == FALSE` means wait forever; `TRUE` means use `Timeout`.

SMB2 handling requires malformed names to fail as not found, non-pipe objects to
fail as invalid device requests, and timeout expiration to fail as timeout.
Win32 `WaitNamedPipe` uses the full `\\server\pipe\pipename` string at its API
surface, but the FSCTL payload carries only the pipe name.

Sources:

- https://learn.microsoft.com/pl-pl/openspecs/windows_protocols/ms-fscc/f030a3b9-539c-4c7b-a893-86b795b9b711
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-smb2/6ea29283-b629-48a5-a7f8-ed7d09d42387
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/4d23fdb5-840e-456a-858f-6a238011179f
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-waitnamedpipea

## Local Risk

`File_WaitNamedPipe` casts the caller buffer to `FILE_PIPE_WAIT_FOR_BUFFER` and
reads `NameLength` before proving that the fixed header exists. It also copies
`NameLength / sizeof(WCHAR)` WCHARs before proving that `NameLength` is even and
fits inside `InputBufferLength - FIELD_OFFSET(..., Name)`.

Because this hook rewrites the FSCTL before calling the native API, the hook must
validate the subset of the FSCTL payload it reads. Invalid shapes can be passed
through to native validation only before Sandboxie dereferences or rewrites
them.

## Acceptance Gate

- `InputBuffer` must be non-null and `InputBufferLength` must cover
  `FIELD_OFFSET(FILE_PIPE_WAIT_FOR_BUFFER, Name)` before `NameLength` is read.
- `NameLength` must be WCHAR-aligned.
- `NameLength` must fit inside the supplied input buffer.
- The rewritten output allocation must be checked before write.
