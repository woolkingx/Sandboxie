---
kind: srev-ledger-entry
id: SREV-015
title: ALPC Connect Proxy Uses Unknown Magic Flags
status: patched-source-level-with-alpc-official-observation-map-needs-windows-runtime-proof
owner: "Sandboxie/core/dll/ipc.c:5399"
spec: docs/plan/srev-015-alpc-connect-flags.md
schema: docs/plan/srev-015-alpc-connect-flags.schema.json
checker: docs/plan/check-srev-015.sh
runtime_gate: "capture `AlpcConnectRequest`, `AlpcConnectSuccess`, and `AlpcConnectFail` for `ntsvcs` / `plugplay` proxy behavior across supported Windows builds before changing accepted flag policy"
---
### SREV-015: ALPC Connect Proxy Uses Unknown Magic Flags

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level ALPC official observation map; needs Windows runtime proof |
| Evidence | Explorer Ohm reported `Sandboxie/core/dll/ipc.c:5399` had comments naming unknown `0x20000` / `0x10000` ALPC flags. The code now uses local ALPC constant names and source comments name SREV-015 at the connection and message-view gates. Microsoft documents ALPC ETW, WPT event/stack names, and debugger posture but does not publish a stable `NtAlpcConnectPort` flag contract. |
| Data | `NtAlpcConnectPort` / `NtAlpcConnectPortEx` flags and `ALPC_PORT_ATTRIBUTES.Flags`. |
| Schema | ALPC route decisions must be based on named, verified flags or captured version matrix, not unknown magic constants. SREV-138 mirror-header proof is required before interpreting captured `ALPC_PORT_ATTRIBUTES` or `ALPC_MESSAGE_VIEW` fields. |
| Topology | Native ALPC connect crosses into Sandboxie proxy/open-true/copy-path logic. |
| Logic Risk | Unknown flags can reject valid Windows shapes or route privileged endpoints inconsistently across Windows builds. |
| Official Shape | `docs/plan/srev-015-alpc-connect-flags.md` records that Microsoft Learn exposes ALPC ETW class, WPT event/stack names, debugger LPC/ALPC posture, and SQOS shape, but not a stable `NtAlpcConnectPort` flag contract. |
| Runtime Capture Matrix | Supported Windows 10/11 x86/x64/ARM64 where built; `ntsvcs`, `plugplay`, non-proxied endpoint, and old-LPC controls; `NtAlpcConnectPort`, `NtAlpcConnectPortEx`, `NtAlpcSendWaitReceivePort`, SbieSvc `AlpcRequestHandler`, and driver endpoint observation; connection flags before/after WOW64 masking, `ALPC_PORT_ATTRIBUTES.Flags`, `SecurityQos`, `MaxMessageLength`, status, endpoint, process image, architecture, Windows build, message-view flags, view mapping, unmap special case, service-side view mask result, ALPC ETW/stack/debugger evidence, SREV-138 mirror-header proof, and negative controls for unexpected connect flags, bad port attributes, non-null ALPC connection info, unknown view bits, missing view/size pointers, message-length mismatch, and non-target endpoint native behavior. |
| Shared Runtime Capture Evidence | Runtime records use `docs/plan/srev-015-138-alpc-runtime-capture.schema.json`; `docs/plan/srev-015-138-alpc-runtime-capture-playbook.md` is the capture procedure; `docs/plan/check-srev-015-138-alpc-runtime-capture.sh` validates the shared ALPC evidence contract. |
| Fix | Existing local ALPC constants from `win32_ntddk.h` are now used in the DLL/service connect and view paths instead of naked `0x20000`, `0x10000`, and `0x40000000` values. Source comments now classify the accepted connection flags and message-view mask as locally observed private ALPC shapes requiring Windows capture plus SREV-138 mirror-header proof before behavior changes. This is a readability/proof-boundary cleanup only; it does not broaden accepted flags. |
| Acceptance Gate | `docs/plan/check-srev-015.sh` proves connect-path naked constants are replaced with local names, stale unknown/numeric-only comments are gone, source comments require Windows proof before accepted-flag changes, and the schema/spec/ledger keep a concrete official-observation and runtime-evidence matrix. `docs/plan/check-srev-015-138-alpc-runtime-capture.sh` validates the shared ALPC evidence playbook and machine-readable schema. Windows gate: capture `AlpcConnectRequest`, `AlpcConnectSuccess`, and `AlpcConnectFail` for `ntsvcs` / `plugplay` proxy behavior across supported Windows builds, with SREV-138 mirror-header proof, before changing accepted flag policy. |
