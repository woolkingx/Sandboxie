---
kind: srev-ledger-entry
id: SREV-323
title: RPCRT Binding String Sentinel Gate
status: comment-classified-after-official-rpc-binding-string-shape-review-no-behavior-change
owner: Sandboxie/core/dll/rpcrt.c
spec: docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.md
schema: docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.schema.json
checker: docs/plan/check-srev-323.py
runtime_gate: Windows RPC binding smoke for null StringBinding, null OutBinding, observed 0x4 sentinel, valid spooler binding rewrite, valid ordinary binding, and invalid string-binding provider-owned error propagation
---
### SREV-323: RPCRT Binding String Sentinel Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | comment classified after official RPC binding-string shape review; no source behavior change |
| Evidence | `RpcRt_RpcBindingFromStringBindingW` rejects `!StringBinding`, `!OutBinding`, and `0x4 == (ULONG_PTR)StringBinding` with `RPC_S_INVALID_ARG` before doing local string comparison, spooler binding rewrite, or native `__sys_RpcBindingFromStringBindingW`. The old comment described the sentinel as a Microsoft 0x4 adjustment and crash avoidance. |
| Data | `RpcRt_RpcBindingFromStringBindingW`, `StringBinding`, `OutBinding`, observed `0x4` sentinel, `RPC_S_INVALID_ARG`, `__sys_RpcBindingFromStringBindingW`, and spooler endpoint rewrite adjacency. |
| Schema | `RPCRT_BINDING_STRING_SENTINEL_GATE` says official `RpcBindingFromStringBinding` owns valid string-binding parsing and official error codes; Sandboxie's wrapper owns only pre-forward local pointer/sentinel rejection plus selected binding-string rewrite policy; null `StringBinding`, null `OutBinding`, and the observed `0x4` sentinel return `RPC_S_INVALID_ARG` before forwarding to `rpcrt4`; the observed `0x4` value is a local sentinel, not an official string-binding shape to interpret; this SREV changes comments and proof only. |
| Topology | `caller StringBinding / OutBinding -> Sandboxie local null/sentinel gate -> optional spooler binding rewrite -> __sys_RpcBindingFromStringBindingW -> optional RpcMgmtSetComTimeout`. The sentinel gate is before `_wcsicmp`, binding rewrite, trace, and native RPCRT call. |
| Logic Risk | Crash wording hides the owner boundary. The official API owns valid string-binding parsing and provider-owned errors; Sandboxie owns only its local invalid pointer/sentinel gate before the native call. Future edits should not reinterpret the `0x4` sentinel as a valid binding string or move the gate after local string operations. |
| Official Shape | `docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.md` records Microsoft `RpcBindingFromStringBinding` and binding-handle creation references. `docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.schema.json` records the JSON Schema draft-07 local `RPCRT_BINDING_STRING_SENTINEL_GATE` contract. |
| Fix | Comment-only source clarification. The source now names SREV-323 and says the observed `0x4` binding-string sentinel is rejected locally, while official `RpcBindingFromStringBinding` owns valid string-binding errors. No null/sentinel predicate, return code, binding rewrite, native call, trace, or timeout behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-323.py` validates the draft-07 schema, official references, source comment, null/sentinel guard before `_wcsicmp` and native forwarding, preserved `RPC_S_INVALID_ARG`, preserved native call, stale crash wording removal, and split ledger fragment; `docs/plan/check-srev-323.sh` is the targeted wrapper. Windows gate: RPC binding smoke for null `StringBinding`, null `OutBinding`, observed `0x4` sentinel, valid spooler binding rewrite, valid ordinary binding, and invalid string-binding provider-owned error propagation. |
