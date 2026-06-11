---
kind: srev-ledger-entry
id: SREV-296
title: GuiProp NonRudeHWND SetProp Suppression
status: patched-comment-topology-no-behavior-change-needs-windows-runtime-policy-proof
owner: Sandboxie/core/dll/guiprop.c
spec: docs/plan/srev-296-guiprop-nonrudehwnd-setprop-suppression.md
schema: docs/plan/srev-296-guiprop-nonrudehwnd-setprop-suppression.schema.json
checker: docs/plan/check-srev-296.py
runtime_gate: Windows fullscreen behavior for apps that set NonRudeHWND still needs targeted runtime proof before policy default changes
---

### SREV-296: GuiProp NonRudeHWND SetProp Suppression

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology; no behavior change; needs Windows runtime proof before policy default changes |
| Evidence | `Gui_InitProp` initializes `Gui_NonRudeHWND_Hack` from `UseNonRudeHwndHack` with default `!Dll_CompartmentMode`. `Gui_SetPropW` and `Gui_SetPropA` return `TRUE` without storing the string-named `NonRudeHWND` property when that flag is enabled. Settings describe `UnrestrictedToken` as preserving the original token and disabling token restrictions; `token.c` maps it to `Token_DuplicateToken`; `GuiServer.cpp` maps it to skipped job UI restrictions. |
| Data | `UseNonRudeHwndHack`, `Gui_NonRudeHWND_Hack`, `Dll_CompartmentMode`, `SetPropW`, `SetPropA`, string-named `NonRudeHWND`, `UnrestrictedToken`, `OriginalToken`, `Token_DuplicateToken`, `Token_Restrict`, and job UI restrictions. |
| Schema | `GUIPROP_NONRUDEHWND_SETPROP_SUPPRESSION` says `UseNonRudeHwndHack` controls the `NonRudeHWND` `SetPropA/W` suppression; `SetPropA/W` reports success without storing the `NonRudeHWND` property when the policy is enabled; `UnrestrictedToken` is a broader token/UI-restriction owner in `token.c` and `GuiServer.cpp`; the default keeps `NonRudeHWND` suppression enabled outside app-compartment mode; this SREV changes comments and proof only. |
| Topology | `UseNonRudeHwndHack -> Gui_NonRudeHWND_Hack -> Gui_SetPropA/W string-name check -> NonRudeHWND reports success without storage`; separate path: `UnrestrictedToken / OriginalToken -> token.c / GuiServer.cpp -> broader token and job UI restriction effects`. |
| Logic Risk | The old source comment tied the narrow property rule to `UnrestrictedToken=y`, which can route maintainers or users toward a broad token bypass when the code already has a narrower compatibility policy. The owner boundary should say that `guiprop.c` owns only the window-property crossing and token/UI-restriction owners live elsewhere. |
| Official Shape | Microsoft documents `SetPropW` as adding or changing a window property-list entry identified by string or atom. Microsoft describes window properties as data assigned to a window and identified by a string name. Microsoft documents restricted tokens and job UI restrictions as separate token/job-object boundaries, not as `SetPropA/W` property behavior. |
| Fix | Comment-only source clarification. The source now names SREV-296 and states that `UseNonRudeHwndHack` controls the `NonRudeHWND` SetProp suppression while `UnrestrictedToken` belongs to token/UI-restriction owners. No setting default, string comparison, return value, atom replacement, access check, or `__sys_SetPropA/W` call changed. |
| Acceptance Gate | `docs/plan/check-srev-296.py` validates the draft-07 schema, official references, source comment, unchanged `Gui_NonRudeHWND_Hack` default, unchanged `NonRudeHWND` suppression checks in ANSI and Unicode paths, stale comment removal, token/UI-restriction owner evidence, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-296.sh` is the targeted wrapper. Runtime gate: Windows fullscreen behavior for apps that set `NonRudeHWND` still needs targeted runtime proof before policy default changes. |
