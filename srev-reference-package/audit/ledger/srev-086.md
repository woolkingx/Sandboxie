---
kind: srev-ledger-entry
id: SREV-086
title: GUI Adobe WM_CREATE Class Shape
status: patched-source-level-after-official-win32-class-registration-createwindowex-wm-n
owner: Sandboxie/core/dll/guiclass.c
spec: docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.md
schema: docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.schema.json
checker: docs/plan/check-srev-086.py
runtime_gate: "Adobe/Acrobat/OWL windows create inside a sandbox with matching class identity through `RegisterClassEx` / `CreateWindowEx` / `WM_NCCREATE` / `WM_CREATE`, and ordinary renamed classes still preserve Sandboxie class isolation"
---
### SREV-086: GUI Adobe WM_CREATE Class Shape

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official Win32 class-registration, CreateWindowEx, WM_NCCREATE, WM_CREATE, CREATESTRUCT, and DefWindowProc shape; needs Windows Adobe/OWL window-create runtime proof |
| Evidence | `Sandboxie/core/dll/guiclass.c` prefixes non-open class names with `Sandbox:BoxName:` during RegisterClass/RegisterClassEx and CreateWindowEx hooks, while a local comment admitted Adobe window classes had a `WM_CREATE` class-name problem and left `com.adobe.ape.stage` / `OWL.*` classification commented out. Microsoft documents `RegisterClassEx` / `CreateWindowEx` class identity, `WM_NCCREATE` / `WM_CREATE` `CREATESTRUCT` delivery, and `CREATESTRUCT.lpszClass` as the class-name-or-atom payload crossing into the app window procedure. |
| Data | Registered class name, CreateWindowEx class name, `WM_NCCREATE` / `WM_CREATE` `CREATESTRUCT.lpszClass`, Sandboxie class prefix, well-known / `NoRenameWinClass` classification, Adobe/OWL compatibility classes, and existing private `KernelCallbackTable[10]` create-struct rewrite. |
| Schema | `GUI_ADOBE_WM_CREATE_CLASS_SHAPE` says `RegisterClassEx` / `CreateWindowEx` class identity is the public Win32 boundary; `WM_NCCREATE` and `WM_CREATE` pass `CREATESTRUCT.lpszClass` across the app wndproc boundary; known class-name-sensitive compatibility classes use `NoRename` rather than relying on private callback offsets; `com.adobe.ape.stage` and `OWL.*` are `NoRename` well-known classes; `GetClassName` remains the public query boundary; private `KernelCallbackTable` offsets are not extended. |
| Topology | Caller class registration crosses into `Gui_RegisterClass*`, then user32 stores the class. Caller creation crosses into `Gui_CreateWindowEx*`, then user32 delivers `WM_NCCREATE` / `WM_CREATE` to the app-owned wndproc with `CREATESTRUCT.lpszClass`. Sandboxie's private create-struct callback remains a compatibility edge, not the official owner of class identity. |
| Logic Risk | A sandbox prefix is legal internal isolation state only while every consumer sees the expected app class identity at documented boundaries. For classes that inspect `CREATESTRUCT.lpszClass` during create, relying on private callback offsets is fragile; the stable shape is to leave known class-sensitive classes unrenamed. |
| Official Shape | `docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.md` records Microsoft `RegisterClassExW`, `WNDCLASSEXW`, `CreateWindowExW`, `WM_NCCREATE`, `WM_CREATE`, `CREATESTRUCTW`, and `DefWindowProcW` references. `docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.schema.json` records the JSON Schema draft-07 local `GUI_ADOBE_WM_CREATE_CLASS_SHAPE` contract. |
| Fix | `Gui_IsWellKnownClass` now classifies `com.adobe.ape.stage` and `OWL.*` as well-known classes, causing `Gui_NoRenameClass` / `Gui_CreateClassNameW/A` to preserve those class names instead of applying the sandbox prefix. |
| Acceptance Gate | `docs/plan/check-srev-086.py` validates the draft-07 schema, official references, local class-rename owner evidence, Adobe/OWL `NoRename` classification, stale FIXME/commented-out classification removal, private callback non-expansion, and ledger entry; `docs/plan/check-srev-086.sh` is the matrix wrapper. Windows gate: Adobe/Acrobat/OWL windows create inside a sandbox with matching class identity through `RegisterClassEx` / `CreateWindowEx` / `WM_NCCREATE` / `WM_CREATE`, and ordinary renamed classes still preserve Sandboxie class isolation. |
