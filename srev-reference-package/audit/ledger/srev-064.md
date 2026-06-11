---
kind: srev-ledger-entry
id: SREV-064
title: RPCRT String Binding Pointer Gate
status: patched-source-level-after-official-rpcbindingfromstringbindingw-parameter-shape
owner: Sandboxie/core/dll/rpcrt.c
spec: docs/plan/srev-064-rpcrt-string-binding-pointer-gate.md
schema: docs/plan/srev-064-rpcrt-string-binding-pointer-gate.schema.json
checker: docs/plan/check-srev-064.py
runtime_gate: "normal RPC W string bindings, spooler dynamic-port rewrite, module preset rewrite, null `StringBinding`, null `OutBinding`, `0x4` sentinel, and `IpcTrace` enabled"
---
### SREV-064: RPCRT String Binding Pointer Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `RpcBindingFromStringBindingW` parameter shape and local wrapper parse/trace analysis; needs Windows RPC spooler/preset runtime proof |
| Evidence | `Sandboxie/core/dll/rpcrt.c` `RpcRt_RpcBindingFromStringBindingW` rejects a known `0x4` sentinel, then parses `StringBinding` with `_wcsicmp`, `wcsstr`, and preset lookup before calling RPCRT4. It also logs `*OutBinding` on the trace path. Microsoft documents `RpcBindingFromStringBindingW` as taking a string-binding pointer and an output binding-handle pointer. Before this patch, null `StringBinding` or null `OutBinding` could cross the local wrapper boundary and crash before/after the real RPCRT4 call. |
| Data | `StringBinding`, `OutBinding`, local RPC port-binding preset lookup, temporary replacement binding string, real RPCRT4 binding-handle output, and optional `IpcTrace` debug output. |
| Schema | `RPCRT_STRING_BINDING_POINTER_GATE` says the wrapper may parse, rewrite, call RPCRT4, or trace only after `StringBinding != NULL`, `StringBinding != (WCHAR *)0x4`, and `OutBinding != NULL`. |
| Topology | Caller pointer-shaped RPC inputs flow into Sandboxie's pre-call rewrite layer, then into RPCRT4, then optionally into trace output. The wrapper owns its own pre-call parser and trace dereference gates. |
| Logic Risk | A compatibility wrapper should not dereference or parse invalid pointer-shaped input while trying to protect a downstream API. Rejecting only the `0x4` sentinel still leaves null pointers able to reach local wide-string parsing or trace dereference. |
| Official Shape | `docs/plan/srev-064-rpcrt-string-binding-pointer-gate.md` records Microsoft `RpcBindingFromStringBindingW` and RPC return-value references. `docs/plan/srev-064-rpcrt-string-binding-pointer-gate.schema.json` records the JSON Schema draft-07 local `RPCRT_STRING_BINDING_POINTER_GATE` contract. |
| Fix | `RpcRt_RpcBindingFromStringBindingW` now rejects null `StringBinding`, null `OutBinding`, and the existing `0x4` sentinel before local parsing, rewriting, RPCRT4 call, or trace dereference. |
| Acceptance Gate | `docs/plan/check-srev-064.py` validates the draft-07 schema, official references, the pre-parse pointer gate, stale sentinel-only gate removal, local parser/trace ordering, and ledger entry; `docs/plan/check-srev-064.sh` is the matrix wrapper. Windows gate: normal RPC W string bindings, spooler dynamic-port rewrite, module preset rewrite, null `StringBinding`, null `OutBinding`, `0x4` sentinel, and `IpcTrace` enabled. |
