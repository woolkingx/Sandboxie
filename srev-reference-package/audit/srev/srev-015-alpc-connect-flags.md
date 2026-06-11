# SREV-015 ALPC Connect Flags

Status: source-level posture after local constant naming and source comment
classification; Windows runtime capture still required.

## Official Surface

Microsoft Learn does not expose a public `NtAlpcConnectPort` or
`ALPC_PORT_ATTRIBUTES.Flags` contract equivalent to the file-system structures
used in earlier SREV items. The official public posture available here is:

- `winternl.h` internal APIs are subject to change and should be dynamically
  loaded when used.
- Legacy LPC is documented as emulated in ALPC on newer Windows, and Microsoft
  points debugger users to ALPC tooling.
- Microsoft documents the ALPC ETW class and WPT event/stack points such as
  `AlpcConnectRequest`, `AlpcConnectSuccess`, and `AlpcConnectFail`.
- `SECURITY_QUALITY_OF_SERVICE` is an official structure for client
  impersonation shape, but it does not define private ALPC flag semantics.

Implication: ALPC flag semantics in this code cannot be treated as officially
specified from Microsoft Learn. The correct next runtime gate is capture across
supported Windows builds, not guessing new flag meanings from online examples.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/devnotes/calling-internal-apis
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc
- https://learn.microsoft.com/en-us/windows/win32/etw/alpc
- https://learn.microsoft.com/en-us/windows-hardware/test/wpt/event
- https://learn.microsoft.com/en-us/windows-hardware/test/wpt/stack-wpa
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_quality_of_service

## Local Shape

`Sandboxie/common/win32_ntddk.h` and `Sandboxie/core/drv/alpc.h` already define
local ALPC constants:

```c
PORT_INFO_WOW64_PROCESS  0x40000000
PORT_INFO_CANIMPERSONATE 0x010000
ALPC_SYNC_CONNECTION     0x020000
ALPC_MESSAGE_FLAG_VIEW   0x40000000
```

Those headers explicitly cite an ALPC paper rather than official Microsoft DDI
documentation. They are useful local names, not proof that the behavior is
stable across Windows releases.

## Patch Boundary

This patch may replace naked constants with existing local names where the code
already has the same behavior. It must not broaden accepted ALPC flags or change
proxy policy without Windows capture evidence.

## Source Comment Contract

The connect path now names SREV-015 at the ALPC gate and says that Sandboxie is
accepting a locally named `ntsvcs` / `plugplay` proxy shape, not an officially
published `NtAlpcConnectPort` flag contract.

The ALPC message-view paths now name SREV-015 at the unmap special case and the
service-side view flag mask. They classify those shapes as locally observed
private ALPC behavior. They must not be broadened by numeric guesswork.

## Runtime Capture Gate

The next legal behavior change requires Windows capture evidence:

```text
target endpoints: \RPC Control\ntsvcs and \RPC Control\plugplay
events: AlpcConnectRequest, AlpcConnectSuccess, AlpcConnectFail
source paths: NtAlpcConnectPort, NtAlpcConnectPortEx, NtAlpcSendWaitReceivePort
data: connection flags, ALPC_PORT_ATTRIBUTES.Flags, message view SendFlags/ReceiveFlags, status, endpoint, process image, Windows build
negative controls: rejected flags preserve current failure behavior
```

Shared capture playbook:

```text
docs/plan/srev-015-138-alpc-runtime-capture-playbook.md
```

Machine-readable evidence schema:

```text
docs/plan/srev-015-138-alpc-runtime-capture.schema.json
```

## Runtime Capture Matrix

The Windows gate is not "the proxy connects". It must prove which private ALPC
flags and view bits are actually present on the supported endpoint paths before
Sandboxie broadens or narrows accepted values.

Required dimensions:

- Windows builds and architecture: supported Windows 10/11 x86, x64, and ARM64
  where the DLL, service, and driver are built.
- Endpoint paths: `\RPC Control\ntsvcs`, `\RPC Control\plugplay`,
  non-proxied ALPC endpoint negative control, and old-LPC
  `max_msg_len == -1` control.
- Source paths: `NtAlpcConnectPort`, `NtAlpcConnectPortEx`,
  `NtAlpcSendWaitReceivePort`, SbieSvc `AlpcRequestHandler`, and driver
  endpoint policy observation.
- Connect capture: connection flags before/after `PORT_INFO_WOW64_PROCESS`
  masking, `ALPC_PORT_ATTRIBUTES.Flags`, `SecurityQos`, `MaxMessageLength`,
  returned status, maximum message length, endpoint, process image, process
  architecture, and Windows build.
- Message-view capture: `SendFlags`, `ReceiveFlags`, `ViewAttrs`, mapped
  `ViewBase`/`ViewSize`, unmap special case, service-side view mask result, and
  reply status.
- ETW/debugger evidence: ALPC ETW class enabled with stack capture where
  available, plus debugger `!alpc` / LPC fallback readback when ETW fields are
  insufficient.
- SREV-138 dependency: `ALPC_PORT_ATTRIBUTES` and `ALPC_MESSAGE_VIEW`
  `sizeof`/`FIELD_OFFSET` mirror proof must match the capture build before the
  SREV-015 flag data is interpreted.
- Machine evidence key: `ALPC_MESSAGE_VIEW sizeof and FIELD_OFFSET proof`.
- Machine evidence key: `mirror-header proof matches capture build`.

Negative controls:

- connection flags other than `ALPC_SYNC_CONNECTION` after WOW64 masking;
- `ALPC_PORT_ATTRIBUTES.Flags` not equal to `PORT_INFO_CANIMPERSONATE`;
- non-null connection info on ALPC path;
- unknown `ALPC_MESSAGE_VIEW` bits outside the locally accepted mask;
- missing `SendView`, `ReceiveView`, or receive-size pointer outside the known
  unmap special case;
- message length mismatch with `PORT_MESSAGE.TotalLength`;
- non-`ntsvcs` / non-`plugplay` endpoint preserving native path behavior.

## Acceptance Gate

- Connect path does not use naked `0x20000`, `0x10000`, or `0x40000000` for the
  already named local ALPC meanings.
- Source comments identify SREV-015 and require Windows capture before changing
  ALPC accepted flags or view masks. SREV-138 mirror-header proof is required
  before interpreting captured ALPC view fields.
- Ledger keeps the issue open for runtime capture rather than pretending the
  semantics are officially proven.
- `docs/plan/check-srev-015-138-alpc-runtime-capture.sh` validates the shared
  ALPC runtime capture playbook and machine-readable evidence schema.
