---
kind: srev-ledger-entry
id: SREV-343
title: Util Registry Existence Dummy Buffer
status: patched-comment-topology-after-official-rtlqueryregistryvalues-direct-query-review-no-behavior-change
owner: Sandboxie/core/drv/util.c
spec: docs/plan/srev-343-util-registry-existence-dummy-buffer.md
schema: docs/plan/srev-343-util-registry-existence-dummy-buffer.schema.json
checker: docs/plan/check-srev-343.py
runtime_gate: Windows registry smoke for existing REG_SZ missing value wrong-type value too-small dummy buffer untrusted hive typecheck and pool allocation observation
---

### SREV-343: Util Registry Existence Dummy Buffer

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `RtlQueryRegistryValues` direct-query review; no behavior change |
| Evidence | `DoesRegValueExist` builds a one-WCHAR `DummyBuffer`, wraps it in an initialized `UNICODE_STRING`, and passes it to `GetRegString`. `GetRegString` uses `RTL_QUERY_REGISTRY_DIRECT`, `RTL_QUERY_REGISTRY_TYPECHECK`, `RTL_QUERY_REGISTRY_NOVALUE`, and `RTL_QUERY_REGISTRY_NOEXPAND`, then calls `RtlQueryRegistryValues`. The old inline comment said a NULL buffer causes a kernel pool leak. |
| Data | `DoesRegValueExist`, `DummyBuffer[1]`, `UNICODE_STRING Dummy`, `GetRegString`, `RTL_QUERY_REGISTRY_TABLE`, `EntryContext`, `RTL_QUERY_REGISTRY_DIRECT`, `RTL_QUERY_REGISTRY_TYPECHECK`, `RTL_QUERY_REGISTRY_NOVALUE`, `RTL_QUERY_REGISTRY_NOEXPAND`, `REG_SZ`, `RTL_QUERY_REGISTRY_TYPECHECK_SHIFT`, `RtlQueryRegistryValues`, `STATUS_SUCCESS`, `STATUS_OBJECT_TYPE_MISMATCH`, and `STATUS_BUFFER_TOO_SMALL`. |
| Schema | `UTIL_REGISTRY_EXISTENCE_DUMMY_BUFFER` says `DoesRegValueExist` owns caller-provided storage for a status-only registry existence probe; `RTL_QUERY_REGISTRY_DIRECT` string data requires `EntryContext` to point to an initialized `UNICODE_STRING`; a NULL `UNICODE_STRING.Buffer` lets `RtlQueryRegistryValues` allocate string storage; the dummy one-WCHAR buffer prevents API allocation during the existence probe; `GetRegString` owns the direct-query and typecheck table shape; `STATUS_SUCCESS`, `STATUS_OBJECT_TYPE_MISMATCH`, and `STATUS_BUFFER_TOO_SMALL` are accepted existence statuses; this SREV changes comments and proof only. |
| Topology | `DoesRegValueExist -> DummyBuffer[1] -> UNICODE_STRING { Length=0, MaximumLength=sizeof(DummyBuffer), Buffer=DummyBuffer } -> GetRegString -> qrt[0].EntryContext = pData -> RTL_QUERY_REGISTRY_DIRECT + RTL_QUERY_REGISTRY_TYPECHECK(REG_SZ) -> RtlQueryRegistryValues -> status-only existence result`. |
| Logic Risk | The old comment described a leak symptom but not the API owner contract. Future edits that replace the one-WCHAR buffer with `NULL` would intentionally enter the `RtlQueryRegistryValues` allocation path while this function has no free owner because it only returns a boolean status. |
| Official Shape | Microsoft documents `RtlQueryRegistryValues` direct mode as storing queried string values through an initialized `UNICODE_STRING`; when `Buffer` is `NULL`, the routine allocates string storage, otherwise it uses caller-provided storage. Microsoft also recommends `RTL_QUERY_REGISTRY_TYPECHECK` with direct queries to prevent overflows and documents bug-check behavior for direct queries without type checking in untrusted hive cases. |
| Fix | Comment-only source clarification. The source now names SREV-343 and explains that the one-WCHAR dummy buffer is caller-owned storage for `RTL_QUERY_REGISTRY_DIRECT`, preventing API allocation during a status-only existence probe. No query flags, `UNICODE_STRING` shape, accepted status set, or registry behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-343.py` validates the draft-07 schema, official references, dummy one-WCHAR storage, initialized `UNICODE_STRING`, `GetRegString` query flags, typecheck default type, accepted status set, stale pool-leak wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-343.sh` is the targeted wrapper. Runtime gate: Windows registry smoke for existing REG_SZ, missing value, wrong-type value, too-small dummy buffer, and untrusted-hive/typecheck behavior, with pool allocation/leak observation if instrumentation is available. |
