# SREV-138: ALPC Local Header Contract

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/alpc.h`, `Sandboxie/common/win32_ntddk.h`, ALPC/LPC call sites in `Sandboxie/core/dll/ipc.c`, `Sandboxie/core/svc/namedpipeserver.cpp`, `Sandboxie/core/svc/PipeServer.cpp`, `Sandboxie/core/drv/ipc_port.c`, Microsoft system error code and SQOS references |
| Output artifact | `docs/plan/srev-138-alpc-local-header-contract.schema.json`, `docs/plan/check-srev-138.py`, `docs/plan/check-srev-138.sh`, ledger fragment |
| Owner | local LPC/ALPC ABI header contract |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint; Windows LPC/ALPC runtime proof remains required |

## Evidence

`Sandboxie/core/drv/alpc.h` was the highest-ranked unnamed reviewable core file
after SREV-137. It defines local copies of LPC/ALPC message and attribute shapes:
`MAX_PORTMSG_LENGTH`, `PORT_MESSAGE`, `PORT_DATA_INFO`,
`ALPC_PORT_ATTRIBUTES`, `ALPC_MESSAGE_VIEW`, `NtCreatePort`,
`NtConnectPort`, `NtSecureConnectPort`, `NtRequestPort`,
`NtRequestWaitReplyPort`, `NtReplyWaitReceivePort`,
`NtImpersonateClientOfPort`, `LpcRequestPort`, and `LpcPortObjectType`.

This is not an ordinary project-owned data structure. It is a local projection
of native Windows LPC/ALPC ABI surfaces. The header itself marks the ALPC
attribute/view block as coming from `LPC-ALPC-paper.pdf`, not from a Microsoft
DDI contract. The same constants and structures also exist in
`Sandboxie/common/win32_ntddk.h`, so any edit must preserve both local mirrors.

Local users treat these shapes as wire/ABI truth:

- `PipeServer.cpp` creates ports with `MAX_PORTMSG_LENGTH` and exchanges
  `PORT_MESSAGE` buffers.
- `DriverAssist.cpp` creates a named port so driver `LpcRequestPort` can send
  messages to the service.
- `dll/ipc.c` intercepts `NtConnectPort`, `NtSecureConnectPort`,
  `NtRequestWaitReplyPort`, and ALPC send/wait/receive, then copies
  `PORT_MESSAGE` and `ALPC_MESSAGE_VIEW` fields through service requests.
- `namedpipeserver.cpp` proxies ALPC messages and relies on
  `ALPC_MESSAGE_FLAG_VIEW`, `ALPC_SYNC_CONNECTION`, `PORT_DATA_INFO`, and
  `ALPC_MESSAGE_VIEW`.
- `drv/ipc_port.c`, `ipc_lsa.c`, `ipc_sam.c`, and `ipc_spl.c` read
  `PORT_MESSAGE` headers from user arguments before endpoint policy.

Microsoft does not publish a normal `Nt*Port` / `ALPC_MESSAGE_VIEW` application
contract in the same way it documents ordinary Win32 APIs. The official
evidence available here is narrower: Microsoft system error codes name
`NtCreatePort`, `NtConnectPort`, `NtRequestPort`, and
`NtRequestWaitReplyPort`, including invalid port attributes and message length
too long; Microsoft documents the ALPC ETW class plus WPT ALPC event/stack
names as observation surfaces; debugger docs say legacy LPC is now emulated in
ALPC and points users at ALPC tooling; Microsoft documents
`SECURITY_QUALITY_OF_SERVICE` as the structure that controls impersonation
level, context tracking, and effective-only behavior.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--500-999-
- https://learn.microsoft.com/en-us/windows/win32/etw/alpc
- https://learn.microsoft.com/en-us/windows-hardware/test/wpt/event
- https://learn.microsoft.com/en-us/windows-hardware/test/wpt/stack-wpa
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_quality_of_service

## Data

`MAX_PORTMSG_LENGTH`, `PORT_MESSAGE.u1.s1.DataLength`,
`PORT_MESSAGE.u1.s1.TotalLength`, `PORT_MESSAGE.u2.s2.Type`,
`PORT_MESSAGE.u2.s2.DataInfoOffset`, `CLIENT_ID`, `MessageId`,
`ClientViewSize`, `CallbackId`, `PORT_DATA_INFO`, `ALPC_PORT_ATTRIBUTES.Flags`,
`SECURITY_QUALITY_OF_SERVICE`, `MaxMessageLength`, `ALPC_MESSAGE_VIEW`,
`ALPC_MESSAGE_FLAG_VIEW`, `ALPC_SYNC_CONNECTION`, `PORT_INFO_CANIMPERSONATE`,
and the imported native port calls.

## Schema

`ALPC_LOCAL_HEADER_CONTRACT` says:

- `alpc.h` is a local ABI header, not the authoritative Windows ALPC schema.
- The ALPC attribute/view block is private-research-derived and must not be
  silently treated as an official Microsoft DDI.
- `Sandboxie/core/drv/alpc.h` and `Sandboxie/common/win32_ntddk.h` must keep the
  shared ALPC constants and structure field names in sync.
- `PORT_MESSAGE` remains the local carrier header for Sandboxie LPC/ALPC
  message parsing.
- `MAX_PORTMSG_LENGTH` remains `328` because service, driver, and wire structs
  allocate fixed buffers around that value.
- Endpoint policy may read payload bytes only after a caller has validated the
  `PORT_MESSAGE` header and the relevant `DataLength`/`TotalLength`/offset
  range for that path.
- Changes to `ALPC_MESSAGE_VIEW` or ALPC flags require Windows runtime capture,
  because source-level checking cannot prove the private ABI shape.

## Topology

The local topology is:

```text
native LPC/ALPC system calls
  -> local alpc.h / win32_ntddk.h ABI projection
  -> DLL hook or service broker copies PORT_MESSAGE / ALPC_MESSAGE_VIEW
  -> driver endpoint policy parses selected PORT_MESSAGE payloads
  -> SbieSvc named-pipe/port proxy forwards or rejects
```

Legal modification topology:

```text
official/public evidence or Windows runtime capture
  -> update both local ALPC header mirrors
  -> update call-site checker/spec for affected wire fields
  -> run Windows ALPC proxy and endpoint-policy smoke
```

## Logic Risk

This header is attractive to "clean up" because many fields are named
`Unknown*`, and the ALPC block has a paper-derived comment. That is exactly why
it should not be opportunistically refactored. A wrong field width, offset, flag,
or maximum message length can break IPC isolation, endpoint filtering,
impersonation, or service proxying while still compiling cleanly. The correct
action for this pass is to pin the local contract and require Windows capture
before any ABI mutation.

## Fix

No source behavior changed. `Sandboxie/core/drv/alpc.h` is now ledger-named as
a local LPC/ALPC ABI contract with synchronized-header and runtime-capture
gates.

## Runtime Capture Matrix

The Windows gate is not "ALPC proxy still works". It must prove that the local
header mirror still matches the private LPC/ALPC shapes Sandboxie copies across
DLL, service, and driver boundaries.

Shared capture playbook:

```text
docs/plan/srev-015-138-alpc-runtime-capture-playbook.md
```

Machine-readable evidence schema:

```text
docs/plan/srev-015-138-alpc-runtime-capture.schema.json
```

Required dimensions:

- Windows builds and architecture: supported Windows 10/11 x86, x64, and ARM64
  where Sandboxie builds the service, DLL, and driver.
- Header mirror proof: `Sandboxie/core/drv/alpc.h` and
  `Sandboxie/common/win32_ntddk.h` have identical shared constants, field
  names, widths, and `sizeof` / `FIELD_OFFSET` values for `PORT_MESSAGE`,
  `PORT_DATA_INFO`, `ALPC_PORT_ATTRIBUTES`, and `ALPC_MESSAGE_VIEW`.
- Machine evidence key: `FIELD_OFFSET values`.
- Negative-control evidence key: `mirror-header sizeof or FIELD_OFFSET drift`.
- Port calls: `NtCreatePort`, `NtConnectPort`, `NtSecureConnectPort`,
  `NtRequestPort`, `NtRequestWaitReplyPort`, `NtReplyWaitReceivePort`,
  `NtImpersonateClientOfPort`, `NtAlpcConnectPort`, and
  `NtAlpcSendWaitReceivePort`.
- Proxy paths: SbieSvc old LPC request/reply through `PipeServer.cpp`, ALPC
  connect through `namedpipeserver.cpp`, DLL ALPC send/wait/receive through
  `dll/ipc.c`, and driver endpoint policy through `ipc_port.c`.
- Message shapes: `DataLength`, `TotalLength`, `Type`, `DataInfoOffset`,
  `ClientId`, `MessageId`, `ClientViewSize`, `CallbackId`, and
  `MAX_PORTMSG_LENGTH` boundary behavior.
- ALPC private shapes: `ALPC_PORT_ATTRIBUTES.Flags`, `SecurityQos`,
  `MaxMessageLength`, `ALPC_MESSAGE_VIEW.SendFlags`, `ReceiveFlags`,
  `ReplyLength`, `MessageId`, `CallbackId`, `ViewBase`, `ViewSize`, and the
  `ALPC_MESSAGE_FLAG_VIEW` mapped-view path.
- Endpoint policy payloads: LSA, SAM, spooler, and dynamic RPC port traffic,
  including malformed short payloads that must not be parsed past validated
  `PORT_MESSAGE` bounds.

Negative controls:

- message longer than `MAX_PORTMSG_LENGTH`;
- `TotalLength < sizeof(PORT_MESSAGE)`;
- `DataLength + sizeof(PORT_MESSAGE) > TotalLength`;
- nonzero `DataInfoOffset` where the path rejects it;
- unknown `ALPC_MESSAGE_VIEW` flags outside the local accepted mask;
- SQOS impersonation settings that do not permit the expected proxy behavior;
- mirror-header `sizeof` or `FIELD_OFFSET` drift between driver and common
  headers.

## Acceptance Gate

`docs/plan/check-srev-138.py` validates the draft-07 schema, official reference
links, `alpc.h` and `win32_ntddk.h` mirror constants/field names, major
call-site usage in service, DLL, and driver code, the SREV-015 ALPC flag
precedent, concrete runtime capture matrix, and the ledger fragment.
`docs/plan/check-srev-138.sh` is the targeted wrapper.
`docs/plan/check-srev-015-138-alpc-runtime-capture.sh` validates the shared
runtime capture playbook and machine-readable evidence schema.

Runtime/build gate: Windows x86/x64/ARM64 service and driver build; ALPC proxy
smoke through `namedpipeserver.cpp`; LPC service request/reply smoke through
`PipeServer.cpp`; driver endpoint-policy traffic for LSA/SAM/spooler/dynamic
ports; mirror-header `sizeof` / `FIELD_OFFSET` proof; malformed message
negative controls; and trace capture proving any future `ALPC_MESSAGE_VIEW`
field mutation.
