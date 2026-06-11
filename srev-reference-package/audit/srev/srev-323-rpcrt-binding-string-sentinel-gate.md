# SREV-323: RPCRT Binding String Sentinel Gate

## Data

`Sandboxie/core/dll/rpcrt.c` hooks `RpcBindingFromStringBindingW` so it can
rewrite selected local RPC binding strings, especially spooler dynamic endpoint
bindings. Before the hook forwards to `rpcrt4`, it rejects null pointers, a null
output pointer, and an observed `0x4` `StringBinding` sentinel.

The relevant data nodes are:

```text
RpcRt_RpcBindingFromStringBindingW
StringBinding
OutBinding
observed 0x4 sentinel
RPC_S_INVALID_ARG
__sys_RpcBindingFromStringBindingW
spooler endpoint rewrite adjacency
```

## Official Shape

Microsoft documents `RpcBindingFromStringBinding` as creating a server binding
handle from a string representation of a binding handle. Its input is a
`StringBinding` pointer and its output is a `Binding` pointer. Official failures
include invalid string binding and invalid argument.

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindingfromstringbinding
```

Microsoft's binding-handle creation guidance composes a string binding, passes
it to `RpcBindingFromStringBinding`, then frees the string binding with
`RpcStringFree`.

```text
https://learn.microsoft.com/en-us/windows/win32/rpc/creating-a-binding-handle
```

## Schema

Local schema:

```text
docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.schema.json
```

`RPCRT_BINDING_STRING_SENTINEL_GATE` says:

- official `RpcBindingFromStringBinding` owns valid string-binding parsing and
  official error codes;
- Sandboxie's wrapper owns only pre-forward local pointer/sentinel rejection and
  selected binding-string rewrite policy;
- null `StringBinding`, null `OutBinding`, and the observed `0x4` sentinel must
  return `RPC_S_INVALID_ARG` before forwarding to `rpcrt4`;
- the `0x4` value is a local observed sentinel, not an official string-binding
  shape to interpret;
- this SREV changes comments and proof only, not binding behavior.

## Topology

```text
caller StringBinding / OutBinding
  -> Sandboxie local null/sentinel gate
  -> optional spooler binding rewrite
  -> __sys_RpcBindingFromStringBindingW
  -> optional RpcMgmtSetComTimeout
```

The sentinel gate is deliberately before any `_wcsicmp`, binding rewrite, trace,
or native RPCRT call.

## Logic Risk

The old comment described the `0x4` value as a Microsoft adjustment and framed
the issue as a crash if passed to the system function. That wording obscures the
owner boundary. The official API owns valid string-binding parsing; Sandboxie
owns only its local invalid pointer/sentinel gate before the native call.

## Fix

Comment-only source clarification. The source now names SREV-323 and says the
observed `0x4` binding-string sentinel is rejected locally, while official
`RpcBindingFromStringBinding` owns valid string-binding errors.

No null/sentinel predicate, return code, binding rewrite, native call, trace, or
timeout behavior changed.

## Acceptance Gate

`docs/plan/check-srev-323.py` validates the draft-07 schema, official Microsoft
references, source comment, null/sentinel guard before `_wcsicmp` and native
forwarding, preserved `RPC_S_INVALID_ARG`, preserved native call, stale crash
wording removal, and split ledger fragment.

Windows gate: RPC binding smoke for null `StringBinding`, null `OutBinding`,
the observed `0x4` sentinel, valid spooler binding rewrite, valid ordinary
binding, and invalid string-binding provider-owned error propagation.
