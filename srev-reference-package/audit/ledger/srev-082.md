---
kind: srev-ledger-entry
id: SREV-082
title: Shell FakeApp QueryInterface Vtable Boundary
status: source-level-verified-existing-hardening-after-official-com-queryinterface-and-i
owner: Sandboxie/core/dll/sh.c
spec: docs/plan/srev-082-sh-fake-shellapp-queryinterface.md
schema: docs/plan/srev-082-sh-fake-shellapp-queryinterface.schema.json
checker: docs/plan/check-srev-082.py
runtime_gate: "scripting clients querying `IUnknown`, `IDispatch`, `IShellDispatch`, or `IShellDispatch2` succeed; clients querying `IShellDispatch3/4/5/6` receive `E_NOINTERFACE` with a null output pointer and do not call beyond the fake vtable"
---
### SREV-082: Shell FakeApp QueryInterface Vtable Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | source-level verified existing hardening after official COM `QueryInterface` and `IShellDispatch2` shape; needs Windows shell automation runtime proof |
| Evidence | `Sandboxie/core/dll/sh.c` synthesizes a `FakeShellApp` object backed by a 39-entry `IShellDispatch2` vtable. The local comment now names the contract directly: `SH32_FakeApp_QI` must not accept `IShellDispatch3/4/5/6` because those interfaces add vtable slots beyond this table. Microsoft documents that `QueryInterface` returns `S_OK` plus an AddRef'd pointer only for supported interfaces, returns `E_NOINTERFACE` with a null output pointer for unsupported interfaces, returns `E_POINTER` for a null output pointer, and exposes a static interface set. |
| Data | FakeShellApp object, requested IID, supported IID set, 39-entry `IShellDispatch2` vtable, unsupported `IShellDispatch3/4/5/6` requests, `ppv` output pointer, and refcount. |
| Schema | `SH_FAKE_SHELLAPP_QUERYINTERFACE` says `FakeShellApp` may return self only for `IUnknown`, `IDispatch`, `IShellDispatch`, and `IShellDispatch2`; successful `QueryInterface` increments refcount; unsupported interfaces set `*ppv` to NULL and return `E_NOINTERFACE`; `IShellDispatch3/4/5/6` must not be accepted by a 39-entry `IShellDispatch2` vtable; null `ppv` returns `E_POINTER`; the supported interface set is static. |
| Topology | `FakeFolderView` / `FakeDesktop` creates or returns `FakeShellApp`; `SH32_FakeApp_QI` owns the boundary between external COM IID requests and the local synthetic vtable. The vtable is the executable projection of the supported IID set. |
| Logic Risk | A fake COM object must not advertise an interface whose vtable contract it does not implement. If a client successfully queries `IShellDispatch3/4/5/6`, the client may legally call later slots that do not exist in the 39-entry local table. |
| Official Shape | `docs/plan/srev-082-sh-fake-shellapp-queryinterface.md` records Microsoft `IUnknown::QueryInterface`, QueryInterface implementation rules, and `IShellDispatch2` references. `docs/plan/srev-082-sh-fake-shellapp-queryinterface.schema.json` records the JSON Schema draft-07 local `SH_FAKE_SHELLAPP_QUERYINTERFACE` contract. |
| Fix | The current source already accepts only `IUnknown`, `IDispatch`, `IShellDispatch`, and `IShellDispatch2`, increments refcount on success, and returns `E_NOINTERFACE` with `*ppv = NULL` for unsupported interfaces. A later comment-only clarification replaced stale risk wording with explicit SREV-082 contract language. This SREV records and gates the existing hardened shape so the comment-admitted risk is classified. |
| Acceptance Gate | `docs/plan/check-srev-082.py` validates the draft-07 schema, official references, accepted IID set, explicit unsupported-interface rejection, 39-entry `IShellDispatch2` vtable, null-output handling, refcount increment on success, and ledger entry; `docs/plan/check-srev-082.sh` is the matrix wrapper. Windows gate: scripting clients querying `IUnknown`, `IDispatch`, `IShellDispatch`, or `IShellDispatch2` succeed; clients querying `IShellDispatch3/4/5/6` receive `E_NOINTERFACE` with a null output pointer and do not call beyond the fake vtable. |
