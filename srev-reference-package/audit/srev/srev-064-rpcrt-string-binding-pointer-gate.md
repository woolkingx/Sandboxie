# SREV-064: RPCRT String Binding Pointer Gate

## Data

`Sandboxie/core/dll/rpcrt.c` wraps `RpcBindingFromStringBindingW` so it can
rewrite selected local RPC string bindings before calling RPCRT4. The wrapper
parses `StringBinding` with wide-string functions, may build a replacement
binding string, calls the real `RpcBindingFromStringBindingW`, and optionally
logs the returned binding handle.

The relevant data nodes are:

```text
StringBinding input pointer
OutBinding output pointer
local RpcPortBinding preset lookup
temporary replacement binding string
real RPCRT4 binding handle output
IpcTrace debug output
```

## Official Shape

Microsoft documents `RpcBindingFromStringBindingW` as taking a pointer to a
string binding and an output pointer for the server binding handle:

```text
https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindingfromstringbindingw
```

Microsoft documents `RPC_STATUS` return values for RPC runtime calls, including
invalid-argument failures:

```text
https://learn.microsoft.com/en-us/windows/win32/rpc/rpc-return-values
```

The API defines parameter shape; it does not make Sandboxie's pre-call
wide-string parsing safe for null or sentinel pointers.

## Schema

Local schema:

```text
docs/plan/srev-064-rpcrt-string-binding-pointer-gate.schema.json
```

Before the wrapper may parse, rewrite, call RPCRT4, or trace the returned
binding handle:

```text
StringBinding != NULL
StringBinding != (WCHAR *)0x4 sentinel
OutBinding != NULL
```

## Topology

```text
caller StringBinding/OutBinding -> Sandboxie RPCRT wrapper parser -> optional string rewrite -> RPCRT4 -> optional trace
```

The wrapper owns only the pre-call rewrite and trace boundary. It may not pass
invalid pointer-shaped input through its own string parser or trace formatter.

## Logic Risk

Before this patch, the wrapper rejected only the known `0x4` sentinel. A null
`StringBinding` could still reach `_wcsicmp`, `wcsstr`, or preset lookup before
the real RPCRT4 function saw it. A null `OutBinding` could still reach the real
call and later the trace path that dereferences `*OutBinding`.

## Fix

`RpcRt_RpcBindingFromStringBindingW` now rejects null `StringBinding`, null
`OutBinding`, and the existing `0x4` sentinel before any local parsing,
rewriting, RPCRT4 call, or trace dereference.

## Acceptance Gate

`docs/plan/check-srev-064.py` validates the draft-07 schema, official reference
links, the single pre-parse pointer gate, stale sentinel-only gate removal, and
ledger entry.

Windows gate: normal W string bindings still resolve through RPCRT4; spooler
dynamic-port rewrite still works; null `StringBinding`, null `OutBinding`, and
the `0x4` sentinel return `RPC_S_INVALID_ARG` without local wrapper crash.
