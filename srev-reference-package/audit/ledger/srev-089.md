---
kind: srev-ledger-entry
id: SREV-089
title: GUI Hook WISPTIS Fake Hook Handle
status: patched-source-level-after-official-setwindowshookexw-wh-mouse-ll-lowlevelmousep
owner: Sandboxie/core/dll/guihook.c
spec: docs/plan/srev-089-guihook-wisptis-fake-hook-handle.md
schema: docs/plan/srev-089-guihook-wisptis-fake-hook-handle.schema.json
checker: docs/plan/check-srev-089.py
runtime_gate: "WISPTIS inside the sandbox receives a successful blocked `SetWindowsHookExW(WH_MOUSE_LL)` result, can later unhook that result without probing arbitrary memory or calling user32 with a fake handle, and ordinary thread-specific / low-level / pseudo-global hook behavior remains unchanged"
---
### SREV-089: GUI Hook WISPTIS Fake Hook Handle

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `SetWindowsHookExW`, `WH_MOUSE_LL`, `LowLevelMouseProc`, hook chaining, and `UnhookWindowsHookEx` handle-owner shape; needs Windows WISPTIS / hook runtime proof |
| Evidence | `Sandboxie/core/dll/guihook.c` blocks WISPTIS `WH_MOUSE_LL` hooks by returning a fake successful `HHOOK`. Microsoft documents `SetWindowsHookExW` as returning a hook handle on success, `WH_MOUSE_LL` as a low-level mouse hook called in the installing process context, and `UnhookWindowsHookEx` as consuming a hook handle obtained from `SetWindowsHookEx`. Before this patch, the WISPTIS block returned the fixed integer `0x12345678`; `Gui_UnhookWindowsHookEx` then classified aligned values as possible Sandboxie `GUI_HOOK*` handles and probed their `eyecatcher`, so the magic integer could enter pointer-probe logic even though it was neither a user32 HHOOK nor a Sandboxie-owned allocation. |
| Data | WISPTIS process image type, `WH_MOUSE_LL` low-level mouse hook request, suppressed `SetWindowsHookExW` result, fake `HHOOK`, `UnhookWindowsHookEx` input, real user32 HHOOK path, and Sandboxie pseudo-global `GUI_HOOK*` handle path. |
| Schema | `GUIHOOK_WISPTIS_FAKE_HOOK_HANDLE` says the WISPTIS `WH_MOUSE_LL` compatibility block returns a non-NULL process-local fake `HHOOK`; the fake handle has an owner-local cookie address rather than a magic integer; `UnhookWindowsHookEx` consumes that fake handle locally before pointer-shape probing; real `HHOOK` values still forward to user32; Sandboxie pseudo-global `GUI_HOOK` pointer handles keep their existing owner path; this SREV does not broaden WISPTIS hook suppression policy. |
| Topology | WISPTIS calls `SetWindowsHookExW(WH_MOUSE_LL)`, crosses into `Gui_SetWindowsHookExW`, receives a process-local fake cookie, and later passes it to `Gui_UnhookWindowsHookEx`, which consumes the cookie locally. Other low-level/thread-specific hooks remain on the user32 path; Sandboxie pseudo-global hooks remain on the `GUI_HOOK*` path. |
| Logic Risk | If Sandboxie synthesizes a successful hook handle, that fake handle must have a local owner identity and a matching unhook path. A fixed aligned integer is not a legal owner shape and can be misclassified by the existing pointer-probe heuristic. |
| Official Shape | `docs/plan/srev-089-guihook-wisptis-fake-hook-handle.md` records Microsoft `SetWindowsHookExW`, `LowLevelMouseProc`, `UnhookWindowsHookEx`, and hooks overview references. `docs/plan/srev-089-guihook-wisptis-fake-hook-handle.schema.json` records the JSON Schema draft-07 local `GUIHOOK_WISPTIS_FAKE_HOOK_HANDLE` contract. |
| Fix | The WISPTIS low-level mouse hook block now returns the address of a process-local static cookie as its fake `HHOOK`. `Gui_UnhookWindowsHookEx` consumes that cookie locally before the existing pointer-alignment and `GUI_HOOK` probing path. |
| Acceptance Gate | `docs/plan/check-srev-089.py` validates the draft-07 schema, official hook references, WISPTIS `WH_MOUSE_LL` block evidence, static fake-cookie declaration, cookie return from `SetWindowsHookExW`, local fake-cookie unhook success before pointer probing, stale magic handle removal, and ledger entry; `docs/plan/check-srev-089.sh` is the matrix wrapper. Windows gate: WISPTIS inside the sandbox receives a successful blocked `SetWindowsHookExW(WH_MOUSE_LL)` result, can later unhook that result without probing arbitrary memory or calling user32 with a fake handle, and ordinary thread-specific / low-level / pseudo-global hook behavior remains unchanged. |
