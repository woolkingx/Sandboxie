# SREV-281: Net Param Device-Control Compartment Boundary

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file_init.c`, `Sandboxie/core/dll/file_pipe.c`, `Sandboxie/core/dll/iphlp.c`, `Sandboxie/install/SbieSettings.ini`, Microsoft `ZwDeviceIoControlFile`, `DeviceIoControl`, IOCTL, and ICMP documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_Init` registration of the `NtDeviceIoControlFile` network-parameter deny hook |
| Acceptance gate | Targeted checker validates official references, hook registration predicate, TCP/NSI IOCTL filter owner, compartment-mode ICMP adjacency, stale ping wording removal, and ledger fragment |

## Data

`File_Init` registers the `NtDeviceIoControlFile` hook only when both gates hold:

```text
!Dll_CompartmentMode
File_IsBlockedNetParam(NULL) == TRUE
```

`File_IsBlockedNetParam` reads the `BlockNetParam` setting, whose installed
default is `y`.

The registered hook is `File_NtDeviceIoControlFile` in `file_pipe.c`. Its local
network-parameter deny logic is narrow:

```text
IoControlCode == 0x00128004  -> path must be \Device\TCP
IoControlCode == 0x00120013  -> path must be \Device\NSI
DenyAccess -> SbieApi_Log(1314, Dll_ImageName) -> STATUS_ACCESS_DENIED
```

`IpHlp_Init` in `iphlp.c` also treats compartment mode as a compatibility
boundary for ICMP: when `Dll_CompartmentMode` is true, the ICMP helper hooks are
skipped and the process keeps the native IP helper route.

## Official Shape

Microsoft documents `ZwDeviceIoControlFile` as sending a control code directly
to a specified device driver. The `IoControlCode` value determines the operation
and the required input/output buffer shape. The same page notes that user-mode
callers use the `NtDeviceIoControlFile` name.

Microsoft documents `DeviceIoControl` as the Win32 API that sends a control
code directly to a specified device driver. The control code identifies the
operation and the device type; buffer shapes depend on the specific control
code.

Microsoft documents IOCTLs as communication between user-mode applications and
drivers or between drivers. Some IOCTLs are public and documented; private
IOCTLs belong to vendor components and can have device-specific shapes.

Microsoft documents ICMP echo through IP Helper APIs: `IcmpCreateFile` opens the
handle used for IPv4 ICMP echo requests, and `IcmpSendEcho` sends IPv4 echo
requests through that handle.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwdeviceiocontrolfile`
- `https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-deviceiocontrol`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/introduction-to-i-o-control-codes`
- `https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpcreatefile`
- `https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpsendecho`

## Schema

Local schema:

```text
docs/plan/srev-281-net-param-device-control-compartment-boundary.schema.json
```

Contract id:

```text
NET_PARAM_DEVICE_CONTROL_COMPARTMENT_BOUNDARY
```

## Boundary

```text
box setting BlockNetParam
  -> File_Init hook registration predicate
  -> non-compartment process only
  -> File_NtDeviceIoControlFile
  -> TCP/NSI network-parameter IOCTL deny
```

The hook registration owner is `File_Init`; the IOCTL deny owner is
`File_NtDeviceIoControlFile`. Compartment mode is a separate topology: it keeps
native device-control and IP helper behavior for App Compartment boxes rather
than applying the non-compartment network-parameter deny hook.

## Topology

```text
Dll_CompartmentMode true
  -> skip File_NtDeviceIoControlFile hook registration
  -> iphlp ICMP hooks also skipped
  -> native IP helper/device-control route

Dll_CompartmentMode false + BlockNetParam true
  -> register File_NtDeviceIoControlFile hook
  -> inspect selected TCP/NSI IOCTLs
  -> deny matching network-parameter control calls
  -> pass all other device-control calls to __sys_NtDeviceIoControlFile
```

## Logic Risk

The old inline comment used an application symptom as the only explanation for
the compartment-mode gate. That hid two owner boundaries: `File_Init` owns hook
registration, while `File_NtDeviceIoControlFile` owns the actual TCP/NSI
network-parameter deny logic. Without that split, a future edit could enable the
device-control hook in compartment mode to make `BlockNetParam` appear
uniform, then break the native ICMP/IP helper path that compartment mode relies
on.

## Fix

Comment-only source clarification. The source now names SREV-281 and states
that compartment mode keeps the native device-control route for ICMP/IP helper
behavior, while the `BlockNetParam` TCP/NSI IOCTL deny hook belongs to
non-compartment boxes. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-281.py` validates the draft-07 schema, official
references, `File_Init` hook predicate, `File_IsBlockedNetParam` default,
`File_NtDeviceIoControlFile` TCP/NSI IOCTL deny shape, `iphlp.c` compartment
ICMP adjacency, stale source wording removal, and ledger fragment.

Runtime gate: Windows network matrix covering non-compartment `BlockNetParam=y`
TCP/NSI denial, non-compartment `BlockNetParam=n` native pass-through,
compartment-mode ICMP echo behavior, normal non-network `NtDeviceIoControlFile`
pass-through, and monitor logging for denied network-parameter control calls.
