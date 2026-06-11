# SREV-338: Session Monitor Object Name Staging

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/session.c`, `Sandboxie/core/drv/obj.c`, SREV-028, SREV-155, SREV-160, SREV-171, SREV-232, Microsoft `ObQueryNameString`, `UNICODE_STRING`, and `IoCreateFileSpecifyDeviceObjectHint` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Session_Api_MonitorPut2` monitor object-name staging buffer |
| Acceptance gate | Targeted checker validates official references, WCHAR-counted staging cap, NUL termination after user and object-name copies, counted object-name length use, stale TODO removal, and ledger fragment |

## Data

`Session_Api_MonitorPut2` receives a user monitor string as a byte length plus a
user pointer. When `check_object_exists` is false, it can pass the user string
and explicit WCHAR counts directly to `Session_MonitorPutEx`.

When `check_object_exists` is true, it stages the string locally in `name`:

- `args->log_len` is converted from bytes to WCHAR count;
- the staged user string is capped at `max_buff = 2048` WCHARs;
- `name` is allocated as `(max_buff + 4) * sizeof(WCHAR)`;
- the user string is copied with `wmemcpy` and explicitly NUL-terminated;
- IPC objects are probed through the `Obj_ObjectTypes` table and
  `ObReferenceObjectByName`;
- pipe objects are probed through `IoCreateFileSpecifyDeviceObjectHint` and
  `ObReferenceObjectByHandle`;
- if an object is found, `Obj_GetNameOrFileName` returns an
  `OBJECT_NAME_INFORMATION.Name` counted `UNICODE_STRING`;
- `Name->Name.Length / sizeof(WCHAR)` is capped at `max_buff`, copied into the
  same local staging buffer, and explicitly NUL-terminated;
- `Session_MonitorPutEx` receives `name` with `lengths == NULL`, so it uses
  `wcslen()` and requires a local NUL-terminated string.

## Official Shape

Microsoft documents `ObQueryNameString` as returning an
`OBJECT_NAME_INFORMATION` whose `Name` member is a `UNICODE_STRING`. The buffer
length supplied to `ObQueryNameString` is in bytes, and the returned object name
has a byte `Length` plus a `MaximumLength` that includes the NUL terminator when
present.

Microsoft documents `UNICODE_STRING.Length` as a byte count that excludes a
trailing NUL when present, and `MaximumLength` as the allocated byte capacity.

Microsoft documents `IoCreateFileSpecifyDeviceObjectHint` as receiving
initialized `OBJECT_ATTRIBUTES`; when not running in the system process
context, callers must use `OBJ_KERNEL_HANDLE`. The documented `ObjectName`
member is a buffered Unicode string naming the file to create or open.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-obquerynamestring`
- `https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-iocreatefilespecifydeviceobjecthint`

## Boundary

```text
user monitor input { byte length, user pointer }
  -> ProbeForRead
  -> WCHAR-counted local staging buffer
  -> optional object-existence probe
  -> counted object-manager name
  -> local NUL-terminated monitor string
  -> Session_MonitorPutEx with lengths == NULL
```

`Obj_GetNameOrFileName` / `Obj_GetName` owns object-manager name acquisition.
`Session_Api_MonitorPut2` owns only the staging conversion from user bytes or
counted object names into a bounded NUL-terminated local string suitable for
`Session_MonitorPutEx`.

## Topology

```text
Session_Api_MonitorPut2
  -> args->log_len bytes / sizeof(WCHAR)
  -> cap to max_buff WCHARs
  -> Mem_Alloc(max_buff + 4 WCHARs)
  -> wmemcpy(user log data, log_len)
  -> name[log_len] = L'\0'
  -> optional IPC/pipe object probe
  -> Obj_GetNameOrFileName
  -> Name->Name.Length / sizeof(WCHAR)
  -> cap to max_buff WCHARs
  -> wmemcpy(object name, log_len)
  -> name[log_len] = L'\0'
  -> Session_MonitorPutEx(... lengths == NULL ...)
```

## Logic Risk

The old TODO asked whether to increase the allocation and an adjacent comment
used a stale buffer-size number. That wording hid the actual contract. The
important invariant is not a larger buffer; it is that the monitor object-name
path converts byte-counted and object-manager-counted strings into a bounded
NUL-terminated local staging string before handing it to the monitor ring writer.

If future work treats the buffer as byte-counted, removes the explicit
terminator, or passes a counted object name directly with `lengths == NULL`,
`Session_MonitorPutEx` can scan beyond the intended extent with `wcslen()`.

## Fix

Comment-only source clarification. The source now names SREV-338, states that
`name` is a WCHAR-counted monitor staging buffer, and explains that the `+4`
allocation slack preserves NUL termination after truncation. The stale
`1028`/TODO wording is removed. No cap, allocation size, object probe, object
name query, copy length, terminator write, monitor ring format, or runtime
behavior changed.

## Acceptance Gate

`docs/plan/check-srev-338.py` validates the draft-07 schema, official
references, `Session_Api_MonitorPut2` user string staging, `max_buff` cap,
`(max_buff + 4) * sizeof(WCHAR)` allocation, explicit NUL termination after
both user and object-name copies, counted `Name->Name.Length` use, monitor
writer `wcslen()` adjacency, stale TODO removal, SREV-028 / SREV-155 /
SREV-160 / SREV-171 / SREV-232 adjacency, combined ledger entry, and split
ledger fragment.

Runtime gate: Windows monitor trace matrix with long user monitor strings,
long object-manager names, exact `max_buff` length, truncation, IPC object
existence checks, pipe object checks, unnamed objects, and stack-trace-enabled
monitor entries.
