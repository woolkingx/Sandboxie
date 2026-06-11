---
kind: srev-ledger-entry
id: SREV-030
title: Service Query Sender Name Shape
status: patched-source-level-after-official-openservicew-and-local-service-query-schema-
owner: "Sandboxie/core/dll/scm_query.c:752-774"
spec: docs/plan/srev-030-service-query-sender-name.md
schema: docs/plan/srev-030-service-query.schema.json
checker: docs/plan/check-srev-030.py
runtime_gate: "legal max, max+1, and boxed-service query paths behave as expected and overlong real names fail before `SbieDll_CallServer`"
---
### SREV-030: Service Query Sender Name Shape

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official OpenServiceW and local SERVICE_QUERY schema analysis; needs Windows SCM query runtime proof |
| Evidence | `Sandboxie/core/dll/scm_query.c:752-774` built `SERVICE_QUERY_REQ` in fixed `WCHAR req_space[384]`, then used `wcscpy(u.req.name, ServiceNm)` before the SbieSvc receiver-side service-name gate could run. |
| Data | Real service object name sent as `SERVICE_QUERY_REQ.name_len` plus trailing `WCHAR name[1]`. |
| Schema | `OpenServiceW` service names are null-terminated service object names with a documented 256-character maximum. Local `SERVICE_QUERY` wire name is `name_len` WCHARs plus one terminating NUL. |
| Topology | DLL SCM query path sends real-service names to SbieSvc; boxed services stay on the local boxed-service query path. |
| Logic Risk | An overlong real service name can overflow the sender's fixed stack union before SbieSvc validates the wire request. |
| Official Shape | `docs/plan/srev-030-service-query-sender-name.md` records Microsoft `OpenServiceW` service-name shape. `docs/plan/srev-030-service-query.schema.json` records the small `SERVICE_QUERY` schema entry. |
| Fix | `Scm_QueryServiceByName` now rejects NULL names, preserves the boxed-service path before the real-service limit, rejects real names over `SCM_SERVICE_NAME_MAX_CHARS`, computes `req_len` before writing, verifies it fits the fixed union, and copies `(name_len + 1) * sizeof(WCHAR)` bytes with `memcpy` instead of `wcscpy`. |
| Acceptance Gate | `docs/plan/check-srev-030.py` validates the `SERVICE_QUERY` schema and sender guard/copy shape; `docs/plan/check-srev-030.sh` is the matrix wrapper. Windows gate: legal max, max+1, and boxed-service query paths behave as expected and overlong real names fail before `SbieDll_CallServer`. |
