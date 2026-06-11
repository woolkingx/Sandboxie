# SREV-153: Spooler Counted Port Name

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/ipc_spl.c`, `Sandboxie/core/drv/ipc_port.c`, SREV-118 counted LSA port-name precedent, Microsoft `OBJECT_NAME_INFORMATION`, `RtlEqualUnicodeString`, `RtlInitUnicodeString`, and MS-RPRN references |
| Output artifact | `docs/plan/srev-153-spooler-counted-port-name.schema.json`, `docs/plan/check-srev-153.py`, `docs/plan/check-srev-153.sh`, ledger fragment |
| Owner | Spooler IPC endpoint object-name gate in `ipc_spl.c` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows spooler endpoint runtime proof remains required |

## Evidence

`Sandboxie/core/drv/ipc_spl.c` became the top unnamed reviewable core file after
SREV-152. It owns the print spooler endpoint gate before the RPC opnum policy
runs. The file checks the current object name for either the dynamic spooler RPC
port on Windows 8.1+ or the legacy `\RPC Control\spoolss` endpoint on Vista+.

Before this SREV, both branches compared `Name->Name.Buffer` with `_wcsicmp`.
That treats `OBJECT_NAME_INFORMATION.Name.Buffer` as an owned C string. The
legal data node is `OBJECT_NAME_INFORMATION.Name`, a counted `UNICODE_STRING`.
SREV-118 fixed the same object-name boundary for LSA endpoint gates.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-obquerynamestring
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wkst/edf6cfc6-80b6-4998-a1cf-43bc5dabc042
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlequalunicodestring
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rprn/5ea67df3-c4e7-45ef-b425-40b8b066d276

## Data

`Ipc_CheckPortRequest_SpoolerPort`, `Ipc_Spl_MatchPortName`,
`OBJECT_NAME_INFORMATION.Name`, `UNICODE_STRING.Length`, `UNICODE_STRING.Buffer`,
`Ipc_Dynamic_Ports.pSpoolerPort->wstrPortName`, `\RPC Control\spoolss`,
`Ipc_GetRpcMsgId`, `Ipc_Filter_Spooler_Msg`, and MS-RPRN spooler RPC opnums.

## Schema

`IPC_SPOOLER_COUNTED_PORT_NAME` says:

- `OBJECT_NAME_INFORMATION.Name` is a counted `UNICODE_STRING`.
- `UNICODE_STRING.Length` is a byte count and does not authorize C-string scans
  over `Name->Name.Buffer`.
- Spooler endpoint matching must compare counted strings with
  `RtlEqualUnicodeString`, using `RtlInitUnicodeString` only for the expected
  NUL-terminated literal or dynamic port name.
- The Windows 8.1+ dynamic spooler port gate still accepts only the cached
  dynamic spooler port name.
- The Vista+ fallback still accepts only `\RPC Control\spoolss`.
- This SREV does not change KPATH-006 RPC payload capture, spooler opnum
  filtering, dynamic-port publication, `OpenPrintSpooler`, or
  `AllowSpoolerPrintToFile` behavior.

## Topology

```text
object manager
  -> OBJECT_NAME_INFORMATION.Name { Length, MaximumLength, Buffer }
  -> ipc_spl.c spooler port-name gate
      -> Ipc_Spl_MatchPortName
          -> RtlInitUnicodeString(expected name)
          -> RtlEqualUnicodeString(Name, expected, TRUE)
      -> Ipc_GetRpcMsgId KPATH-006 payload capture
      -> Ipc_Filter_Spooler_Msg MS-RPRN opnum policy
```

## Logic Risk

The old port-name gates crossed from counted kernel object-name data to
NUL-terminated C-string comparison. Even if the common `ObQueryNameString` path
often supplies a terminator, `UNICODE_STRING.Length` remains the authoritative
string extent and `_wcsicmp` is the wrong operator for this boundary. The policy
owner should decide spooler access only after the object-name shape is validated
with a counted-string comparison.

KPATH-006 still owns the unresolved local-RPC payload shape. This SREV fixes the
earlier object-name gate and deliberately leaves byte-20 opnum capture and the
spooler allow/deny table unchanged.

## Fix

`ipc_spl.c` now has `Ipc_Spl_MatchPortName`, which initializes the expected port
name as a `UNICODE_STRING` and compares it with `Name->Name` using
`RtlEqualUnicodeString(..., TRUE)`. The dynamic spooler port branch and legacy
`\RPC Control\spoolss` branch no longer call `_wcsicmp` on `Name->Name.Buffer`.

## Acceptance Gate

`docs/plan/check-srev-153.py` validates the draft-07 schema, official
references, counted spooler port-name helper, removal of `_wcsicmp` object-name
comparison from `ipc_spl.c`, preservation of KPATH-006 `Ipc_GetRpcMsgId`
routing, preservation of the existing spooler opnum deny table, and the ledger
fragment. `docs/plan/check-srev-153.sh` is the matrix wrapper.

Runtime/build gate: Windows driver build for `ipc_spl.c`; object-name
instrumentation proving dynamic spooler and `\RPC Control\spoolss` endpoint
names match by counted length, including buffers without a trailing NUL; normal
spooler print traffic; blocked mutating MS-RPRN operations; unchanged KPATH-006
RPC payload-shape capture.
