# SREV-015 / SREV-138: ALPC Runtime Capture Playbook

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema |
| Input artifact | SREV-015, SREV-138, `Sandboxie/core/dll/ipc.c`, `Sandboxie/core/svc/namedpipeserver.cpp`, `Sandboxie/core/drv/alpc.h`, `Sandboxie/common/win32_ntddk.h`, Microsoft ALPC ETW / LPC debugger / SQOS documentation |
| Output artifact | `docs/plan/srev-015-138-alpc-runtime-capture.schema.json`, `docs/plan/check-srev-015-138-alpc-runtime-capture.py`, runtime capture checklist |
| Owner | ALPC runtime evidence contract for SREV-015 and SREV-138 |
| Acceptance gate | targeted checker validates source/spec adjacency and the evidence schema; Windows capture remains the runtime gate |

## Official Surface

Microsoft's public surface does not define the private `NtAlpcConnectPort`
flag ABI or `ALPC_MESSAGE_VIEW` memory layout used by Sandboxie. The official
surfaces available for this gate are observational:

- ALPC ETW class can be enabled through NT Kernel logging with
  `EVENT_TRACE_FLAG_ALPC`.
- WPT event and stack profiles name ALPC connect, send, receive, wait, and
  close observation points such as `AlpcConnectRequest`,
  `AlpcConnectSuccess`, and `AlpcConnectFail`.
- ALPC ETW event types identify send, receive, wait-for-reply,
  wait-for-new-message, and stop-waiting events.
- Legacy LPC debugger documentation says LPC is now emulated in ALPC and points
  debugger users at ALPC tooling.
- `SECURITY_QUALITY_OF_SERVICE` defines impersonation level, context tracking,
  and effective-only data used when a client connects to a server.

Official references:

```text
https://learn.microsoft.com/en-us/windows/win32/etw/alpc
https://learn.microsoft.com/en-us/windows-hardware/test/wpt/event
https://learn.microsoft.com/en-us/windows-hardware/test/wpt/stack-wpa
https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_quality_of_service
```

Therefore the legal route is:

```text
official observation surface -> Windows runtime capture -> local ABI evidence -> source/schema decision
```

The legal route is not:

```text
local header names -> inferred Windows ABI truth -> behavior change
```

## Data

Each capture record must identify:

- Windows build, architecture, Sandboxie build, box name, process image, and
  capture tool.
- Endpoint path: `\RPC Control\ntsvcs`, `\RPC Control\plugplay`, an unrelated
  ALPC endpoint negative control, or the old-LPC control.
- Source path: `NtAlpcConnectPort`, `NtAlpcConnectPortEx`,
  `NtAlpcSendWaitReceivePort`, SbieSvc `AlpcRequestHandler`, or driver
  endpoint policy.
- Machine label: `SbieSvc AlpcRequestHandler` is the service-side ALPC proxy
  capture source path.
- Machine label: `driver endpoint policy` is the driver-side ALPC/LPC payload
  parsing capture source path.
- Local ABI mirror values: `sizeof` and `FIELD_OFFSET` for `PORT_MESSAGE`,
  `PORT_DATA_INFO`, `ALPC_PORT_ATTRIBUTES`, and `ALPC_MESSAGE_VIEW` from both
  `Sandboxie/core/drv/alpc.h` and `Sandboxie/common/win32_ntddk.h`.
- Connect values: pre-mask flags, post-WOW64-mask flags,
  `ALPC_PORT_ATTRIBUTES.Flags`, `SecurityQos`, `MaxMessageLength`, status,
  endpoint, process identity, and native/proxy route.
- Message-view values: `SendFlags`, `ReceiveFlags`, `ReplyLength`,
  `MessageId`, `CallbackId`, `ViewBase`, `ViewSize`, unmap special case,
  service-side view mask result, and reply status.
- PORT_MESSAGE values: `DataLength`, `TotalLength`, `Type`,
  `DataInfoOffset`, `ClientId`, `MessageId`, `ClientViewSize`, `CallbackId`,
  and whether the message is within `MAX_PORTMSG_LENGTH`.
- Evidence coordinates: ETW trace path, debugger command transcript, source
  build commit, capture timestamp, and operator notes.

## Schema

Machine-readable capture records use:

```text
docs/plan/srev-015-138-alpc-runtime-capture.schema.json
```

The schema is intentionally about evidence, not source code. A record is valid
only if it names the build, endpoint, source path, mirror-header proof,
connect/message values, and negative-control result.

## Topology

```text
Windows ALPC/LPC runtime
  -> ETW/debugger/build probe capture
  -> evidence record
  -> SREV-138 mirror-header interpretation
  -> SREV-015 flag/view policy decision
```

SREV-138 must be interpreted before SREV-015:

```text
mirror-header sizeof/FIELD_OFFSET proof
  -> captured ALPC_PORT_ATTRIBUTES / ALPC_MESSAGE_VIEW fields are readable
  -> accepted flag policy can be evaluated
```

If mirror-header proof fails, SREV-015 flag values are not legal evidence.

## Required Captures

Minimum positive paths:

| Capture | Endpoint | Source Path | Required Proof |
|---|---|---|---|
| ALPC connect ntsvcs | `\RPC Control\ntsvcs` | `NtAlpcConnectPort` or `NtAlpcConnectPortEx` | `ALPC_SYNC_CONNECTION`, `PORT_INFO_CANIMPERSONATE`, SQOS, status, process identity |
| ALPC connect plugplay | `\RPC Control\plugplay` | `NtAlpcConnectPort` or `NtAlpcConnectPortEx` | same as above |
| ALPC send/wait view | proxied endpoint | `NtAlpcSendWaitReceivePort` | `ALPC_MESSAGE_FLAG_VIEW`, view base/size, reply status |
| SbieSvc proxy | proxied endpoint | `AlpcRequestHandler` | service-side view mask, native call status, reply shape |
| Driver endpoint policy | LSA/SAM/spooler/dynamic | `ipc_port.c` route | validated `PORT_MESSAGE` header before payload parse |

Minimum negative controls:

| Control | Expected Result |
|---|---|
| Unknown connect flag after WOW64 masking | rejected or native-preserved according to current policy |
| `ALPC_PORT_ATTRIBUTES.Flags` not equal to `PORT_INFO_CANIMPERSONATE` | rejected or native-preserved according to current policy |
| Non-null connection info on ALPC path | current failure behavior preserved |
| Unknown `ALPC_MESSAGE_VIEW` bits | rejected before service-side native call |
| Missing `SendView` / `ReceiveView` outside unmap special case | current failure behavior preserved |
| Message longer than `MAX_PORTMSG_LENGTH` | not copied into fixed local buffer |
| `TotalLength < sizeof(PORT_MESSAGE)` | payload not parsed |
| `DataLength + sizeof(PORT_MESSAGE) > TotalLength` | payload not parsed |
| Non-`ntsvcs` / non-`plugplay` endpoint | native behavior preserved |

## Logic Risk

ALPC/LPC capture is a topology dependency, not a cosmetic proof. A wrong
private field offset can make all downstream endpoint/RPC conclusions false
while source checks remain green. Treat each capture record as valid only for
the exact Windows build and architecture it names.

## Acceptance Gate

Linux/source gate:

```bash
bash docs/plan/check-srev-015-138-alpc-runtime-capture.sh
bash docs/plan/check-srev-015.sh
bash docs/plan/check-srev-138.sh
```

Windows gate:

1. Build Sandboxie service, DLL, and driver for the target architecture.
2. Capture mirror-header `sizeof` / `FIELD_OFFSET` values from the same build.
3. Enable ALPC ETW and stack capture where available.
4. Run `ntsvcs`, `plugplay`, ALPC send/wait view, old-LPC, and endpoint-policy
   paths.
5. Store one JSON record per build/architecture/endpoint/source-path/control.
6. Validate records against
   `docs/plan/srev-015-138-alpc-runtime-capture.schema.json`.
7. Only after records validate and SREV-138 mirror-header proof holds may SREV-015
   accepted flags or view masks be changed.
