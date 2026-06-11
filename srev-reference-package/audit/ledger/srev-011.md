---
kind: srev-ledger-entry
id: SREV-011
title: Named-Pipe LPC Connect Reply Copies Caller Length Instead Of Reply Length
status: patched-source-level-after-official-internal-api-posture-and-local-reply-schema-
owner: "Sandboxie/core/dll/ipc.c:5477"
spec: docs/plan/srev-011-named-pipe-lpc-reply-shape.md
schema: docs/plan/srev-011-named-pipe-lpc-reply-shape.schema.json
checker: docs/plan/check-srev-011.sh
runtime_gate: "proxy `\\RPC Control\\ntsvcs` / `plugplay` old-LPC connect with non-empty connection info and confirm behavior is unchanged"
---
### SREV-011: Named-Pipe LPC Connect Reply Copies Caller Length Instead Of Reply Length

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official/internal API posture and local reply schema analysis; needs Windows runtime proof |
| Evidence | Explorer Ohm reports `Sandboxie/core/dll/ipc.c:5477` has a no-op clamp `if (rpl->info_len < info_len) info_len = info_len;`, followed by `memcpy` from `rpl->info_data`. |
| Data | `NAMED_PIPE_LPC_CONNECT_RPL { MSG_HEADER h, handle, max_msg_len, info_len, info_data[1] }`. |
| Schema | Copy length must be bounded by both caller output capacity and actual reply payload length; reply header length must cover `info_len`. |
| Topology | SbieSvc reply crosses into hooked DLL caller buffer. |
| Logic Risk | A short or malformed service reply can make the DLL read past reply payload and copy unowned memory to the caller buffer. |
| Official Shape | `docs/plan/srev-011-named-pipe-lpc-reply-shape.md` records Microsoft's internal-API posture for `winternl.h` and the local `NAMED_PIPE_LPC_CONNECT_RPL` wire schema owned by Sandboxie. |
| Fix | `Ipc_NamedPipeProxy` now rejects successful replies whose `h.length` does not cover the fixed reply fields, verifies `info_len` fits inside the returned payload, and copies only `min(reply_info_len, caller_capacity)`. |
| Acceptance Gate | `docs/plan/check-srev-011.sh` proves the no-op clamp is gone, reply length covers `info_data + info_len`, and copy length is the min of service reply and caller capacity. Windows gate: proxy `\RPC Control\ntsvcs` / `plugplay` old-LPC connect with non-empty connection info and confirm behavior is unchanged. |
