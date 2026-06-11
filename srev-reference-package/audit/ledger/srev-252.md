---
kind: srev-ledger-entry
id: SREV-252
title: Advapi Window Object Security Bypass
status: patched-comment-topology-after-official-setsecurityinfo-getsecurityinfo-window-object-review-no-behavior-change
owner: Sandboxie/core/dll/advapi.c
spec: docs/plan/srev-252-advapi-window-object-security-bypass.md
schema: docs/plan/srev-252-advapi-window-object-security-bypass.schema.json
checker: docs/plan/check-srev-252.py
runtime_gate: Windows Chrome 38 or compatible Chrome sandbox launch matrix capturing SetSecurityInfo arguments before predicate narrowing
---

### SREV-252: Advapi Window Object Security Bypass

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `SetSecurityInfo`, `GetSecurityInfo`, and window-object review; no behavior change |
| Evidence | `advapi.c` has a paired Chrome 38 compatibility bypass in `AdvApi_SetSecurityInfo` and `Ntmarta_SetSecurityInfo`: Chrome image, `ObjectType == SE_WINDOW_OBJECT`, null handle, and return `ERROR_SUCCESS`. The same file also has `GetSecurityInfo` fallback logic that retries DACL reads on `Gui_Dummy_WinSta` for `SE_WINDOW_OBJECT`. SREV-116 owns the official pointer-depth shape for `GetSecurityInfo`; SREV-126 owns the returned `Gui_Dummy_WinSta` handle-ownership boundary. |
| Data | `AdvApi_SetSecurityInfo`, `Ntmarta_SetSecurityInfo`, `Dll_ImageType`, `DLL_IMAGE_GOOGLE_CHROME`, `SE_WINDOW_OBJECT`, null `handle`, `SecurityInfo`, `DACL_SECURITY_INFORMATION`, `Gui_Dummy_WinSta`, and `ERROR_SUCCESS`. |
| Schema | `ADVAPI_WINDOW_OBJECT_SECURITY_BYPASS` says `SetSecurityInfo` sets security information for an object identified by a handle; `SE_WINDOW_OBJECT` is the object type for window stations and desktops; Sandboxie's Chrome compatibility bypass returns `ERROR_SUCCESS` only for Chrome `SE_WINDOW_OBJECT` calls with a null handle; `AdvApi_SetSecurityInfo` and `Ntmarta_SetSecurityInfo` must keep the same bypass predicate until Windows Chrome runtime proof supports narrowing it; `GetSecurityInfo` dummy-window-station DACL fallback remains owned by SREV-116 and SREV-126 adjacency; this SREV does not change DACL mutation behavior, handle ownership, hook selection, ntmarta forwarding, or Chrome image detection. |
| Topology | Advapi path is `Chrome -> AdvApi_SetSecurityInfo -> SE_WINDOW_OBJECT + NULL handle -> report ERROR_SUCCESS without native call`. Ntmarta path is the same through `Ntmarta_SetSecurityInfo`. Adjacent read path is `GetSecurityInfo DACL read fails on window object -> Gui_Dummy_WinSta exists -> retry GetSecurityInfo on dummy window station`. |
| Logic Risk | The old comments made the paired bypasses look like unexplained Chrome residue. The real topology is a Chrome-specific null-handle window-object security compatibility bypass, adjacent to the dummy window-station DACL read fallback. Narrowing the bypass to `DACL_SECURITY_INFORMATION` from Linux source review would be a behavior change without the required Windows runtime matrix. |
| Official Shape | `docs/plan/srev-252-advapi-window-object-security-bypass.md` records Microsoft `SetSecurityInfo`, `GetSecurityInfo`, and `SE_OBJECT_TYPE` references. `docs/plan/srev-252-advapi-window-object-security-bypass.schema.json` records the JSON Schema draft-07 local `ADVAPI_WINDOW_OBJECT_SECURITY_BYPASS` contract. |
| Fix | Comment-only source clarification. `AdvApi_SetSecurityInfo` now names the Chrome null window-station/desktop security-handle probe. `Ntmarta_SetSecurityInfo` now says it owns the same Chrome null window-object security bypass. No condition, return value, native forwarding call, hook wiring, or `GetSecurityInfo` fallback changed. |
| Acceptance Gate | `docs/plan/check-srev-252.py` validates the draft-07 schema, official reference links, SREV-116/SREV-126 adjacency, paired bypass comments, unchanged bypass predicates and forwarding calls, removal of stale Chrome 38 hack wording from those sites, and the ledger fragment; `docs/plan/check-srev-252.sh` is the targeted wrapper. Runtime gate: Windows Chrome 38 or compatible Chrome sandbox launch matrix that captures `SetSecurityInfo` / `Ntmarta_SetSecurityInfo` arguments for null window-object calls before any predicate narrowing. |
