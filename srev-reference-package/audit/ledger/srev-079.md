---
kind: srev-ledger-entry
id: SREV-079
title: Registry Existence Buffer Status
status: patched-source-level-after-official-rtlqueryregistryvalues-direct-buffer-status-
owner: Sandboxie/core/drv/util.c
spec: docs/plan/srev-079-registry-existence-buffer-status.md
schema: docs/plan/srev-079-registry-existence-buffer-status.schema.json
checker: docs/plan/check-srev-079.py
runtime_gate: existing short string, existing long string, existing different registry type, missing value, and missing key all map to the intended boolean existence result without using a NULL direct-query buffer
---
### SREV-079: Registry Existence Buffer Status

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `RtlQueryRegistryValues` direct-buffer status shape and local registry existence probe analysis; needs Windows registry runtime proof |
| Evidence | `Sandboxie/core/drv/util.c` `DoesRegValueExist` uses a one-character initialized `UNICODE_STRING` dummy buffer because the local comment says passing a NULL buffer can leak kernel pool memory. Microsoft documents `RTL_QUERY_REGISTRY_DIRECT` as requiring `EntryContext` to point to an initialized `UNICODE_STRING` for string data, and documents `STATUS_BUFFER_TOO_SMALL` when the direct buffer is too small. Before this patch, the existence predicate returned true only for `STATUS_SUCCESS` or `STATUS_OBJECT_TYPE_MISMATCH`, so an existing long string value could be reported absent when the dummy buffer was too small. |
| Data | Registry key path, value name, initialized dummy `UNICODE_STRING`, `RtlQueryRegistryValues` direct-query status, and boolean existence result. |
| Schema | `REGISTRY_EXISTENCE_BUFFER_STATUS` says the probe must supply a non-NULL initialized `UNICODE_STRING`; `STATUS_SUCCESS`, `STATUS_OBJECT_TYPE_MISMATCH`, and `STATUS_BUFFER_TOO_SMALL` all prove the queried value exists; missing-key and unrelated failure statuses remain false. |
| Topology | `DoesRegValueExist` calls `GetRegString`, which calls `RtlQueryRegistryValues` with `RTL_QUERY_REGISTRY_DIRECT`; `DoesRegValueExist` owns only the NTSTATUS-to-boolean existence projection and must not reinterpret a too-small dummy output buffer as a missing registry value. |
| Logic Risk | The dummy buffer prevents the NULL-buffer leak path, but it is intentionally too small for normal strings. Treating `STATUS_BUFFER_TOO_SMALL` as false makes existence depend on the dummy buffer size rather than on registry state. |
| Official Shape | `docs/plan/srev-079-registry-existence-buffer-status.md` records Microsoft `RtlQueryRegistryValues` references. `docs/plan/srev-079-registry-existence-buffer-status.schema.json` records the JSON Schema draft-07 local `REGISTRY_EXISTENCE_BUFFER_STATUS` contract. |
| Fix | `DoesRegValueExist` now treats `STATUS_BUFFER_TOO_SMALL` as true, preserving the non-NULL dummy buffer workaround while aligning the existence predicate with the official direct-query status shape. |
| Acceptance Gate | `docs/plan/check-srev-079.py` validates the draft-07 schema, official reference, initialized dummy `UNICODE_STRING`, non-NULL direct-query buffer, `STATUS_BUFFER_TOO_SMALL` inclusion in the existence predicate, and ledger entry; `docs/plan/check-srev-079.sh` is the matrix wrapper. Windows gate: existing short string, existing long string, existing different registry type, missing value, and missing key all map to the intended boolean existence result without using a NULL direct-query buffer. |
