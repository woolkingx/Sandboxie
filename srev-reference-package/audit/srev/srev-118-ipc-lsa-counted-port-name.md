# SREV-118 IPC LSA Counted Port Name

## Data

Owner file:

```text
Sandboxie/core/drv/ipc_lsa.c
```

Reviewed nodes:

```text
Ipc_CheckPortRequest_Lsa
Ipc_CheckPortRequest_LsaEP
Ipc_Lsa_MatchPortName
OBJECT_NAME_INFORMATION
UNICODE_STRING Name
RtlInitUnicodeString
RtlEqualUnicodeString
\LsaAuthenticationPort
\RPC Control\lsasspirpc
\RPC Control\LSARPC_ENDPOINT
```

Related existing gates:

```text
docs/plan/kpath-004-lsad-spec.md
docs/plan/check-kpath-004.sh
docs/plan/2026-05-27-sandboxie-kernel-path-audit.md#KPATH-006
docs/plan/check-kpath-006.sh
```

## Schema

`IPC_LSA_COUNTED_PORT_NAME` defines these local contracts:

- `OBJECT_NAME_INFORMATION.Name` is a counted `UNICODE_STRING`.
- `UNICODE_STRING.Length` is a byte count and does not prove that
  `Buffer` is NUL-terminated.
- LSA endpoint matching must compare counted strings, not C-string scans over
  `Name->Name.Buffer`.
- `Ipc_CheckPortRequest_Lsa` continues to accept only
  `\LsaAuthenticationPort` and `\RPC Control\lsasspirpc` when
  `ipc_block_password` is enabled.
- `Ipc_CheckPortRequest_LsaEP` continues to accept only
  `\RPC Control\LSARPC_ENDPOINT` unless `OpenLsaEndpoint` is enabled.
- This SREV does not change MS-LSAD opnum policy, password-change detection,
  KPATH-004 secret/private-data denial, KPATH-006 RPC payload capture, or
  `OpenLsaEndpoint` behavior.

## Topology

```text
object manager
  -> OBJECT_NAME_INFORMATION.Name { Length, MaximumLength, Buffer }
  -> ipc_lsa.c port-name gate
      -> Ipc_Lsa_MatchPortName
          -> RtlInitUnicodeString(expected literal)
          -> RtlEqualUnicodeString(Name, expected, TRUE)
      -> LSA authentication-port password filter
      -> LSARPC endpoint opnum filter
```

## Logic Risk

The old port-name gates checked `Name->Name.Length` and then called
`_wcsicmp(Name->Name.Buffer, ...)`. `OBJECT_NAME_INFORMATION.Name.Buffer` is a
`UNICODE_STRING` buffer, not an owned C string. A correct length can identify
the candidate shape, but it does not add a trailing NUL or make a C-string
routine legal. `_wcsicmp` may read past the counted object-name buffer until it
finds a zero WCHAR elsewhere.

KPATH-004 and KPATH-006 already own the deeper LSARPC method-policy and payload
parser questions. This SREV fixes the earlier object-name boundary before those
policy gates run.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-obquerynamestring
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wkst/edf6cfc6-80b6-4998-a1cf-43bc5dabc042
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlequalunicodestring
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring

## Fix

`ipc_lsa.c` now has `Ipc_Lsa_MatchPortName`, which initializes the expected port
literal as a `UNICODE_STRING` and compares it with `Name->Name` using
`RtlEqualUnicodeString(..., TRUE)`. The three LSA port-name gates no longer call
`_wcsicmp` on `Name->Name.Buffer`.

No LSARPC opnum allow/deny decision, RPC message-id extraction, trace capture,
password-change scan, event-log message, `OpenLsaEndpoint` escape hatch, or
Windows-version branch changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-118.py
bash docs/plan/check-srev-118.sh
```

Runtime/build gate still required:

- Windows driver build for `ipc_lsa.c`.
- Object-name test or instrumentation proving LSA endpoint names match by
  counted length, including buffers without a trailing NUL.
- Normal `\LsaAuthenticationPort`, `\RPC Control\lsasspirpc`, and
  `\RPC Control\LSARPC_ENDPOINT` traffic still reaches the same password and
  LSARPC policy filters.
- KPATH-004/KPATH-006 runtime gates still apply for secret/private-data opnum
  policy and RPC payload-shape capture.
