---
kind: srev-ledger-entry
id: SREV-316
title: Ntmarta Window Security Hook Selection
status: patched source-level comments after official window-object security shape; needs Windows runtime proof
owner: Sandboxie/core/dll/advapi.c
spec: docs/plan/srev-316-ntmarta-window-security-hook-selection.md
schema: docs/plan/srev-316-ntmarta-window-security-hook-selection.schema.json
checker: docs/plan/check-srev-316.py
runtime_gate: Windows Chrome/Acrobat desktop creation and window-station security smoke with Advapi32/ntmarta call capture
---

### SREV-316: Ntmarta Window Security Hook Selection

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level comments after official window-object security shape; needs Windows runtime proof |
| Evidence | `ldr.c` registers `ntmarta.dll` with `Ntmarta_Init`. `Ntmarta_Init` resolves ntmarta `GetSecurityInfo`, publishes it for the desktop-hack process set when `OpenWndStation` is false, installs the ntmarta `GetSecurityInfo` hook only for 32-bit Acrobat Reader, and publishes ntmarta `SetSecurityInfo` only for 64-bit Chrome when Advapi32 did not resolve the API path. `Ntmarta_GetSecurityInfo` retries failed `SE_WINDOW_OBJECT` DACL queries against `Gui_Dummy_WinSta`; `Ntmarta_SetSecurityInfo` keeps the SREV-252 Chrome null-window-object bypass. |
| Data | `ntmarta.dll`, `Ntmarta_Init`, `Ntmarta_GetSecurityInfo`, `Ntmarta_SetSecurityInfo`, `GetSecurityInfo`, `SetSecurityInfo`, `SE_WINDOW_OBJECT`, `DACL_SECURITY_INFORMATION`, `Gui_Dummy_WinSta`, `UseSbieDeskHack`, `OpenWndStation`, Chrome, Firefox, Acrobat Reader, Advapi32, and `Gui_CreateDesktopW`. |
| Schema | `NTMARTA_WINDOW_SECURITY_HOOK_SELECTION` says `GetSecurityInfo` and `SetSecurityInfo` are handle plus `SE_OBJECT_TYPE` security APIs; `SE_WINDOW_OBJECT` means a local window station or desktop object; `CreateDesktopW` with NULL security attributes inherits from the parent window station; `Ntmarta_Init` owns only ntmarta hook selection and function-pointer publication; `Ntmarta_GetSecurityInfo` fallback remains owned by SREV-116 and SREV-126; `Ntmarta_SetSecurityInfo` Chrome null window-object bypass remains owned by SREV-252; this SREV changes comments and proof only, not hook predicates or behavior. |
| Topology | `ntmarta.dll load -> Ldr_Dlls entry -> Ntmarta_Init -> Ldr_GetProcAddrNew(GetSecurityInfo) -> desktop-hack image/config predicate and !OpenWndStation -> publish __sys_GetSecurityInfo -> 32-bit Acrobat Reader only installs Ntmarta_GetSecurityInfo hook -> native ntmarta call -> failed SE_WINDOW_OBJECT DACL + Gui_Dummy_WinSta -> retry dummy window station`. 64-bit Chrome path: `Ntmarta_Init -> Ldr_GetProcAddrNew(SetSecurityInfo) -> publish __sys_SetSecurityInfo only as Advapi32-missing fallback -> Ntmarta_SetSecurityInfo -> SREV-252 Chrome null SE_WINDOW_OBJECT bypass -> native ntmarta SetSecurityInfo otherwise`. |
| Logic Risk | Calling the loader path a generic Chrome/Acrobat workaround hides that different adjacent entries own different semantics: SREV-116 owns `GetSecurityInfo` API/out-param shape, SREV-126 owns `Gui_Dummy_WinSta` handle ownership, and SREV-252 owns the Chrome null-window-object `SetSecurityInfo` bypass. Without that map, future edits could widen ntmarta hooks, change image predicates, or treat the dummy window station as general window-object security truth. |
| Official Shape | Microsoft documents `GetSecurityInfo` and `SetSecurityInfo` as handle plus `SE_OBJECT_TYPE` APIs. Microsoft documents `SE_WINDOW_OBJECT` as a local window-station or desktop object. Microsoft documents window stations and desktops as securable objects and documents `CreateDesktopW` NULL security attributes as inheriting the desktop security descriptor from the parent window station. |
| Fix | `ldr.c` now names the `ntmarta.dll` entry as the SREV-316 window-object security hook-selection path. `Ntmarta_Init` comments now identify the SREV-116/SREV-126 dummy-window-station fallback, the SREV-252 Chrome `SetSecurityInfo` fallback, and the Advapi32/ntmarta delay-loading recursion boundary. No hook predicate, image condition, `OpenWndStation` condition, export lookup, function-pointer assignment, native call, retry condition, or return value changed. |
| Acceptance Gate | `docs/plan/check-srev-316.py` validates the draft-07 schema, official references, loader table registration, `GetSecurityInfo` and `SetSecurityInfo` resolution, hook/publication predicates, no broad ntmarta hook installation, source comments, SREV adjacency, `Gui_CreateDesktopW` NULL-security retry adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-316.sh` is the targeted wrapper. Runtime gate: Windows Chrome/Acrobat desktop creation and window-station security smoke with call capture for Advapi32 and ntmarta `GetSecurityInfo` / `SetSecurityInfo`, proving no recursion, no widened process/image predicate, and no regression in the SREV-116/SREV-126/SREV-252 adjacent paths. |
