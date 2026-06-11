# SREV-343: Util Registry Existence Dummy Buffer

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/util.c` and Microsoft `RtlQueryRegistryValues` / `RTL_QUERY_REGISTRY_DIRECT` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `DoesRegValueExist` caller-owned `UNICODE_STRING` buffer for registry existence probes |
| Acceptance gate | Targeted checker validates official references, dummy one-WCHAR buffer, initialized `UNICODE_STRING`, `GetRegString` direct-query flags, no NULL buffer, stale pool-leak wording removal, and ledger fragment |

## Data

`DoesRegValueExist` checks whether a registry value exists without needing the
actual string data. It creates:

```text
WCHAR DummyBuffer[1] = {0}
UNICODE_STRING Dummy = { 0, sizeof(DummyBuffer), DummyBuffer }
```

and passes that initialized `UNICODE_STRING` to `GetRegString`.

`GetRegString` uses `RtlQueryRegistryValues` with these key flags:

```text
RTL_QUERY_REGISTRY_REQUIRED
RTL_QUERY_REGISTRY_DIRECT
RTL_QUERY_REGISTRY_TYPECHECK
RTL_QUERY_REGISTRY_NOVALUE
RTL_QUERY_REGISTRY_NOEXPAND
```

The existence check treats `STATUS_SUCCESS`, `STATUS_OBJECT_TYPE_MISMATCH`, and
`STATUS_BUFFER_TOO_SMALL` as proof that the value exists or at least reached the
typed direct-query boundary.

## Official Shape

Microsoft documents `RtlQueryRegistryValues` as storing a queried value into the
buffer pointed to by `EntryContext` when `RTL_QUERY_REGISTRY_DIRECT` is set. For
string data such as `REG_SZ`, `EntryContext` must point to an initialized
`UNICODE_STRING`. If `UNICODE_STRING.Buffer` is `NULL`, the routine allocates
storage for the string data; otherwise, it stores data into the caller-supplied
buffer.

Microsoft also says callers using `RTL_QUERY_REGISTRY_DIRECT` should set
`RTL_QUERY_REGISTRY_TYPECHECK` to guard against overflow, and Windows can bug
check when direct registry queries omit type checking for untrusted hives.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlqueryregistryvalues`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x139--kernel-security-check-failure`

## Boundary

```text
DoesRegValueExist
  -> caller-owned WCHAR[1]
  -> initialized UNICODE_STRING
  -> GetRegString
  -> RtlQueryRegistryValues + RTL_QUERY_REGISTRY_DIRECT
  -> status-only existence result
```

`DoesRegValueExist` owns the dummy buffer because it is intentionally not asking
`RtlQueryRegistryValues` to allocate string storage. `GetRegString` owns the
direct query table shape.

## Topology

```text
DummyBuffer[1]
  -> UNICODE_STRING { Length = 0, MaximumLength = sizeof(DummyBuffer), Buffer = DummyBuffer }
  -> qrt[0].EntryContext = pData
  -> RTL_QUERY_REGISTRY_DIRECT
  -> RTL_QUERY_REGISTRY_TYPECHECK with REG_SZ
  -> RtlQueryRegistryValues
  -> status in { SUCCESS, OBJECT_TYPE_MISMATCH, BUFFER_TOO_SMALL } means value exists
```

## Logic Risk

The old inline comment described a NULL buffer causing a kernel pool leak. The
real local invariant is the official direct-query allocation rule: a NULL
`UNICODE_STRING.Buffer` transfers allocation responsibility to
`RtlQueryRegistryValues`, while this caller only needs a status result. Future
edits that replace the one-WCHAR buffer with `NULL` would create an allocation
path with no local free owner.

## Fix

Comment-only source clarification. The source now names SREV-343 and explains
that the one-WCHAR dummy buffer is caller-owned storage for
`RTL_QUERY_REGISTRY_DIRECT`, preventing API allocation during a status-only
existence probe. No query flags, `UNICODE_STRING` shape, accepted status set, or
registry behavior changed.

## Acceptance Gate

`docs/plan/check-srev-343.py` validates the draft-07 schema, official
references, dummy one-WCHAR storage, initialized `UNICODE_STRING`, `GetRegString`
query flags, typecheck default type, accepted status set, stale pool-leak wording
removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows registry smoke for existing REG_SZ, missing value,
wrong-type value, too-small dummy buffer, and untrusted-hive/typecheck behavior,
with pool allocation/leak observation if instrumentation is available.
