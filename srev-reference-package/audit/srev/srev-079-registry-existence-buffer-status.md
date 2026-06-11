# SREV-079: Registry Existence Buffer Status

## Data

`Sandboxie/core/drv/util.c` uses `DoesRegValueExist` as a registry value
existence probe. The helper passes a one-character `UNICODE_STRING` buffer into
`GetRegString`, because the local comment says a NULL buffer can leak memory in
the kernel.

The relevant data nodes are:

```text
registry key path
registry value name
initialized dummy UNICODE_STRING
RtlQueryRegistryValues direct query
NTSTATUS result
boolean existence result
```

## Official Shape

Microsoft documents `RtlQueryRegistryValues` with `RTL_QUERY_REGISTRY_DIRECT` as
storing the result in the buffer pointed to by `EntryContext`. For string data,
`EntryContext` must point to an initialized `UNICODE_STRING`. If the buffer is
too small, the direct query can return `STATUS_BUFFER_TOO_SMALL`.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlqueryregistryvalues
```

## Schema

Local schema:

```text
docs/plan/srev-079-registry-existence-buffer-status.schema.json
```

The existence-probe contract is:

```text
the probe supplies an initialized non-NULL UNICODE_STRING buffer
STATUS_SUCCESS means the value exists and fit the dummy buffer
STATUS_OBJECT_TYPE_MISMATCH means the value exists but has a different type shape
STATUS_BUFFER_TOO_SMALL means the value exists but did not fit the dummy buffer
missing-key and other failure statuses remain false
```

## Topology

```text
DoesRegValueExist -> GetRegString -> RtlQueryRegistryValues direct query -> NTSTATUS -> boolean existence
```

`DoesRegValueExist` owns only the status-to-existence projection. It must not
turn a too-small dummy output buffer into "value missing".

## Logic Risk

Before this patch, `DoesRegValueExist` returned true only for `STATUS_SUCCESS`
or `STATUS_OBJECT_TYPE_MISMATCH`. A legitimate existing `REG_SZ` /
`REG_EXPAND_SZ` value longer than the one-character dummy buffer could be
reported as absent if the direct registry query returned `STATUS_BUFFER_TOO_SMALL`.

## Fix

`DoesRegValueExist` now treats `STATUS_BUFFER_TOO_SMALL` as true, preserving the
dummy-buffer workaround while aligning the existence predicate with the official
direct-query status shape.

## Acceptance Gate

`docs/plan/check-srev-079.py` validates the draft-07 schema, official
`RtlQueryRegistryValues` reference, initialized dummy `UNICODE_STRING`, and
`STATUS_BUFFER_TOO_SMALL` inclusion in the existence predicate.

Windows gate: existing short string, existing long string, existing different
registry type, missing value, and missing key all map to the intended boolean
existence result without using a NULL direct-query buffer.
