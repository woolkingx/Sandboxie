---
kind: srev-ledger-entry
id: SREV-016
title: AccessCheckByType Hook Grants Full Access As Compatibility Bypass
status: patched-source-level-after-official-authorization-api-semantics-needs-bits-wuau-
owner: "Sandboxie/core/dll/advapi.c:555"
spec: docs/plan/srev-016-accesscheckbytype-bypass.md
schema: docs/plan/srev-016-accesscheckbytype-bypass.schema.json
checker: docs/plan/check-srev-016.sh
runtime_gate: BITS/WUAU/WUAUCLT smoke proves the compatibility bypass still unblocks the intended false-negative without granting unrelated requested rights
---
### SREV-016: AccessCheckByType Hook Grants Full Access As Compatibility Bypass

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official authorization API semantics; needs BITS/WUAU runtime proof |
| Evidence | Explorer Ohm reports `Sandboxie/core/dll/advapi.c:555` sets `GrantedAccess = 0xFFFFFFFF` and `AccessStatus = TRUE` for a Win7-era BITS/WUAU workaround. |
| Data | `AccessCheckByType` security descriptor, token, desired access, object-type list, generic mapping. |
| Schema | Windows authorization owns the access decision; a compatibility patch must constrain exact false-negative shape. |
| Topology | Hooked Advapi authorization result crosses into app/service behavior. |
| Logic Risk | Callers receive full access instead of a shaped access result. |
| Official Shape | `docs/plan/srev-016-accesscheckbytype-bypass.md` records Microsoft `AccessCheckByType` / `AccessCheck` output semantics for `DesiredAccess`, `MAXIMUM_ALLOWED`, `GenericMapping`, `GrantedAccess`, and `AccessStatus`. |
| Fix | Existing BITS/WUAU compatibility bypass scope is preserved, but bypasses now report `DesiredAccess` rather than `0xFFFFFFFF`; `MAXIMUM_ALLOWED` uses `GenericMapping->GenericAll` when available; the native NT hook returns `STATUS_SUCCESS` instead of `TRUE`. |
| Acceptance Gate | `docs/plan/check-srev-016.sh` proves no AccessCheckByType bypass reports `0xFFFFFFFF`, Win32 bypasses remain successful, and the NT hook returns `STATUS_SUCCESS`. Windows gate: BITS/WUAU/WUAUCLT smoke proves the compatibility bypass still unblocks the intended false-negative without granting unrelated requested rights. |
