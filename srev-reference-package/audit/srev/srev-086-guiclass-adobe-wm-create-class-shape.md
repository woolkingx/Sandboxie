# SREV-086: GUI Adobe WM_CREATE Class Shape

## Data

`Sandboxie/core/dll/guiclass.c` owns sandbox window-class renaming for the DLL
side GUI boundary. The comment-admitted data shape in this file is:

```text
registered window class name
CreateWindowEx lpClassName
WM_NCCREATE / WM_CREATE CREATESTRUCT.lpszClass
Sandbox:BoxName: class prefix
well-known / NoRename window-class allowlist
Adobe/OWL class compatibility
private KernelCallbackTable create-struct rewrite
```

## Official Shape

Microsoft documents `RegisterClassExW` as registering a window class for later
use by `CreateWindow` / `CreateWindowEx`.

Microsoft documents `WNDCLASSEXW.lpszClassName` as a null-terminated class-name
string or a class atom. String class names are limited to 256 characters.

Microsoft documents `CreateWindowExW.lpClassName` as a null-terminated string or
class atom identifying a registered or predefined class name.

Microsoft documents `WM_NCCREATE` as being delivered before `WM_CREATE`; both
messages carry a `CREATESTRUCT` pointer in `lParam`. For `WM_NCCREATE`, the
`CREATESTRUCT` members are identical to the parameters of `CreateWindowEx`.

Microsoft documents `CREATESTRUCTW.lpszClass` as a pointer to a
null-terminated string or atom that specifies the class name of the new window.
The same page warns that callers should not obtain the class name by reading
this member because it can contain a local atom; `GetClassName` is the public
query boundary.

Microsoft documents `DefWindowProcW` as receiving the same message parameters
as the application window procedure for default processing.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerclassexw
https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-wndclassexw
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createwindowexw
https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-nccreate
https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-create
https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-createstructw
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-defwindowprocw
```

## Schema

Local schema:

```text
docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.schema.json
```

The class-shape contract is:

```text
RegisterClassEx/CreateWindowEx class identity is the public Win32 boundary
WM_NCCREATE and WM_CREATE pass CREATESTRUCT.lpszClass across the app wndproc boundary
known class-name-sensitive compatibility classes use NoRename rather than relying on private callback offsets
com.adobe.ape.stage and OWL.* are classified as NoRename well-known classes
GetClassName remains the public query boundary for class names
private KernelCallbackTable offsets are not extended by this SREV
```

## Topology

```text
caller RegisterClassEx / RegisterClass
  -> Gui_RegisterClass* class-name rewrite
  -> user32 class table
  -> caller CreateWindowEx
  -> Gui_CreateWindowEx* class-name rewrite
  -> user32 WM_NCCREATE / WM_CREATE delivery
  -> app-owned WindowProc receives CREATESTRUCT.lpszClass
```

Sandboxie also has a private fallback edge:

```text
PEB KernelCallbackTable[10]
  -> Gui_CREATESTRUCT_Handler strips Sandbox:BoxName:
  -> original win32k/user callback
  -> Gui_CREATESTRUCT_Restore before DefWindowProc
```

That callback edge is not the official owner of the class-name contract. It is
a compatibility patch around the documented `CREATESTRUCT` boundary.

## Logic Risk

Sandboxie renames non-open class names by prefixing `Sandbox:BoxName:` during
registration and creation. That is useful isolation state, but `WM_NCCREATE` and
`WM_CREATE` legally expose the create-time class identity to the application
window procedure through `CREATESTRUCT.lpszClass`.

The existing source already names the dangerous shape: some Adobe/OWL classes
have a `WM_CREATE` problem when class names are renamed. Depending on the
private `KernelCallbackTable[10]` create-struct rewrite for those classes is a
fragile path because the official API contract is the class-name value crossing
`RegisterClassEx` / `CreateWindowEx` / `CREATESTRUCT`, not the private callback
offset.

The shortest legal fix is to classify the already-named Adobe/OWL classes as
well-known `NoRename` classes. This preserves the application-owned class name
through registration, creation, class-info lookup, and `WM_CREATE` delivery
without expanding the private callback hook.

## Fix

`Gui_IsWellKnownClass` now treats `com.adobe.ape.stage` and `OWL.*` as
well-known classes. Because `Gui_NoRenameClass` treats all well-known classes as
`NoRenameWinClass`, `Gui_CreateClassNameW/A` leaves those class names unchanged
instead of adding the sandbox prefix.

## Acceptance Gate

`docs/plan/check-srev-086.py` validates the draft-07 schema, official Win32
references, local class-rename owner evidence, Adobe/OWL `NoRename`
classification, stale FIXME/commented-out classification removal, private
callback non-expansion, and ledger entry.

Windows gate: Adobe/Acrobat/OWL windows create inside a sandbox with matching
class identity through `RegisterClassEx` / `CreateWindowEx` /
`WM_NCCREATE` / `WM_CREATE`, and ordinary renamed classes still preserve
Sandboxie class isolation. Source-level gates do not prove this runtime path.
