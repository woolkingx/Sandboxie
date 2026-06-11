---
kind: srev-ledger-entry
id: SREV-005
title: SbieSvc PortRequest Reads Message ID Before Minimum Header Check
status: patched-source-level-after-official-lpc-alpc-carrier-posture-and-local-msg-heade
owner: "Sandboxie/core/svc/PipeServer.cpp:793-794"
spec: docs/plan/srev-005-portrequest-message-header-spec.md
schema: docs/plan/srev-005-portrequest-message-header-spec.schema.json
checker: docs/plan/check-srev-005.sh
runtime_gate: "malformed short-message fuzz for lengths 0-7 never reaches `CallTarget`; normal multi-chunk broker calls still work"
---
### SREV-005: SbieSvc PortRequest Reads Message ID Before Minimum Header Check

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official LPC/ALPC carrier posture and local `MSG_HEADER` schema analysis; needs Windows malformed-message proof |
| Evidence | Explorer Newton reports `Sandboxie/core/svc/PipeServer.cpp:793-794` reads `msg_Data[1]` as a message id before proving `msg->u1.s1.DataLength >= sizeof(MSG_HEADER)`; `Sandboxie/core/svc/msgids.h:159` defines the expected `MSG_HEADER` shape. |
| Data | First LPC/ALPC fragment carrying `MSG_HEADER { length, msgid/status }`. |
| Schema | A first fragment shorter than `sizeof(MSG_HEADER)` is not a legal broker request and must be rejected before any `msg_Data[]` field access. |
| Topology | Raw port-message payload crosses into SbieSvc broker dispatch. |
| Logic Risk | A malformed 0-7 byte request can read beyond the received message data and poison message id, sequence handling, or partial-request state. |
| Official Shape | `docs/plan/srev-005-portrequest-message-header-spec.md` records Microsoft LPC/ALPC as the carrier/debug surface and keeps Sandboxie's `MSG_HEADER` as the local payload schema. |
| Fix | `PipeServer::PortRequest` now rejects first chunks with `DataLength < sizeof(MSG_HEADER)` before reading `msg_Data[1]`, touching the sequence byte at offset 3, or reading `msg_Data[0]`. |
| Acceptance Gate | `docs/plan/check-srev-005.sh` proves the minimum-header gate precedes `msg_Data` access. Windows gate: malformed short-message fuzz for lengths 0-7 never reaches `CallTarget`; normal multi-chunk broker calls still work. |
