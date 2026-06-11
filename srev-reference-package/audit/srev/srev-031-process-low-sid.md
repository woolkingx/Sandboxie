# SREV-031: Process Low Inject SID Validation

## Finding

`Sandboxie/core/drv/process_low.c` accepts an optional per-box SID from SbieSvc
during `API_INJECT_COMPLETE`. The old code probed `SECURITY_MAX_SID_SIZE` bytes,
then called `RtlLengthSid(pSID)` and copied that many bytes with `memcpy`.

`RtlLengthSid` has an official precondition: the SID must be valid first. A
malformed `SubAuthorityCount` can make the returned length undefined. That
length then controls allocation and persistent process-owned SID storage used by
the token rewrite path.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlvalidsid`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtllengthsid`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlcopysid`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_sid`

Relevant contract:

- `SID` is variable-length.
- `RtlValidSid` validates SID revision and subauthority count.
- `RtlLengthSid` returns the byte length only for a valid SID; otherwise its
  return value is undefined.
- `RtlCopySid` copies a SID into a caller-allocated destination and returns
  `STATUS_BUFFER_TOO_SMALL` if the destination length is insufficient.

## Local Schema

Small machine-readable schema:

```text
docs/plan/srev-031-process-low-sid.schema.json
```

Data:

```text
API_INJECT_COMPLETE
  parms[1] = process id
  parms[2] = optional PSID from SbieSvc
  parms[3] = injection error code
```

The SID is optional. When present it must be readable up to
`SECURITY_MAX_SID_SIZE`, valid per `RtlValidSid`, and copied into process-owned
pool storage using its validated `RtlLengthSid` byte size.

## Source Change

`Process_Low_Api_InjectComplete` now:

- initializes `status`;
- validates SID shape with `RtlValidSid` before `RtlLengthSid`;
- rejects `sid_length > SECURITY_MAX_SID_SIZE`;
- checks `Mem_Alloc`;
- copies with `RtlCopySid`;
- frees and clears the destination on copy failure;
- preserves the successful injection event while returning the SID-shape error
  if the optional SID is malformed.

`PROCESS.SandboxieLogonSid` is now typed as `PSID`, matching its actual usage.

## Acceptance Gate

Source-level gate:

- `docs/plan/check-srev-031.py` validates the small SID schema and source guard
  shape.
- `RtlValidSid` must appear before `RtlLengthSid`.
- Raw `memcpy(proc->SandboxieLogonSid, pSID, sid_length)` must not remain.

Windows runtime gate:

- SbieSvc-provided valid per-box SID is copied and later used by token rewrite.
- NULL SID keeps the existing anonymous-logon fallback behavior.
- Malformed SID with invalid revision or extreme `SubAuthorityCount` fails
  before `RtlLengthSid` / token rewrite.
