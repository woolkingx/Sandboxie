# SREV-210: Dialog Template Class Name Capacity

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/dll/guidlg.c` was the top unnamed reviewable core file after
SREV-209. It owns the user32 dialog-template hook path used when Sandboxie
renames GUI classes and titles for boxed windows.

`guidlg.c` intercepts `CreateDialogIndirectParam*` and
`DialogBoxIndirectParam*`, calls `Gui_CreateDialogTemplate`, and uses the
rewritten template only when that helper returns a non-NULL pointer. The helper
is generated twice from `Sandboxie/core/dll/guidlg.h`: once for standard
`DLGTEMPLATE` and once for extended `DLGTEMPLATEEX`.

Before this fix, `guidlg.h` used two stack arrays with 256 entries:
`old_clsnm[256]` and `new_clsnm[256]`. The parser stores the dialog class at
index 0 and each control class at index `i + 1`, but it trusted
`tmpl->cDlgItems` directly. A legal template count of 256 would require 257
entries and write past the stack arrays. The success cleanup loop also used the
item-loop index, so it could free the dialog class early and miss the last item
class allocation.

## Data

`guidlg.c`, `guidlg.h`, `Gui_CreateDialogTemplate`,
`Gui_CreateDialogTemplate1`, `Gui_CreateDialogTemplate2`,
`Gui_CreateDialogIndirectParamAorW`, `Gui_DialogBoxIndirectParamAorW`,
`DLGTEMPLATE`, `DLGTEMPLATEEX`, `DLGITEMTEMPLATE`, `DLGITEMTEMPLATEEX`,
`cDlgItems`, dialog class array, control class arrays, `Gui_CreateClassNameW`,
`Gui_CreateTitleW`, `Dll_Alloc`, and `Gui_Free`.

## Official Shape

Microsoft documents `DLGTEMPLATE.cdit` as the number of items in a standard
dialog box template. The standard header is followed by the menu, class, title,
optional font data, and then one `DLGITEMTEMPLATE` block per item.

Microsoft documents `DLGITEMTEMPLATE` as the per-control template block. Each
block is followed by variable-length class, title, and creation-data arrays.

Microsoft documents `DLGTEMPLATEEX.cDlgItems` as a `WORD` count of controls in
an extended dialog box template. It also documents that an extended template is
selected when the `signature` field is `0xFFFF`.

Microsoft documents `CreateDialogIndirectParamW` as accepting either standard
or extended templates in memory. After the call returns, the caller may free
the template because user32 only needs it to start the dialog.

References:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-dlgtemplate`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-dlgitemtemplate`
- `https://learn.microsoft.com/en-us/windows/win32/dlgbox/dlgtemplateex`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createdialogindirectparamw`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dialogboxindirectparamw`

## Schema

`GUI_DIALOG_TEMPLATE_CLASS_NAME_CAPACITY` says:

- `guidlg.c` owns the dialog hook boundary and fallback behavior.
- `guidlg.h` owns the generated standard and extended template rewrite helper.
- The legal template item count comes from the official template header, not
  from local array capacity.
- The local class-name rewrite state stores one dialog-class slot plus one slot
  per control.
- If `cDlgItems` cannot fit in the local state, the helper must fail before
  parsing item classes.
- A failed rewrite returns `NULL`; the caller then passes the original template
  to user32.
- Every successful or failed rewrite path must release temporary renamed class
  and title buffers exactly once.

## Topology

```text
CreateDialogIndirectParam*/DialogBoxIndirectParam*
-> Gui_CreateDialogTemplate(template)
-> select standard DLGTEMPLATE or extended DLGTEMPLATEEX helper
-> validate cDlgItems against local class-name rewrite capacity
-> parse dialog class and cDlgItems control classes
-> allocate rewritten template
-> call user32 with rewritten template
-> free rewritten template after user32 returns
```

Failure topology:

```text
template cDlgItems >= local capacity
-> Gui_CreateDialogTemplate returns NULL
-> wrapper keeps original lpTemplate
-> user32 owns normal template interpretation
```

## Logic Risk

The official template count is a `WORD`, while Sandboxie's temporary class-name
rewrite state had 256 slots. The code needs `cDlgItems + 1` slots because slot
0 belongs to the dialog class and slots 1..N belong to controls. Treating the
official count as if it already fit the local state can corrupt stack memory
before user32 sees the template.

The cleanup loop had a separate correctness risk: rewritten class names were
created during the parse pass but freed during the copy loop using the wrong
index range. That could leak the last control class rewrite and could free the
dialog class allocation before all copy logic had finished using the class
state.

## Fix

`guidlg.h` now names `GUI_DLG_CLASS_NAME_CAPACITY`, uses it for both class-name
state arrays, and rejects `cDlgItems >= GUI_DLG_CLASS_NAME_CAPACITY` before
parsing item classes. It initializes the state arrays and title pointers, routes
temporary allocation failures through one cleanup label, and frees all class
rewrite allocations with a bounded `0..cDlgItems` loop after successful copy or
failed rewrite.

The wrappers in `guidlg.c` already have the safe fallback shape: the rewritten
template replaces `lpTemplate` only when `Gui_CreateDialogTemplate` returns a
non-NULL pointer.

## Acceptance Gate

`docs/plan/check-srev-210.py` validates the draft-07 schema, official
references, source-level capacity guard, initialized cleanup state, success and
failure cleanup loops, absence of the stale fixed-size arrays, split ledger
fragment, and the wrapper fail-open behavior that keeps the original template
when rewrite fails.

Runtime/build gate: Windows DLL build plus dialog smoke tests for standard and
extended templates with 0, 1, 255, and 256+ controls. The 256+ case must not
overwrite stack state and should fall back to the original template; normal
class/title rewriting must still work for supported counts.
