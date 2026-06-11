#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-210 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-210 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema_path = ROOT / "docs/plan/srev-210-dialog-template-class-name-capacity.schema.json"
schema = json.loads(schema_path.read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-210 failed: schema is not draft-07")
if schema.get("id") != "GUI_DIALOG_TEMPLATE_CLASS_NAME_CAPACITY":
    raise SystemExit("SREV-210 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guidlg.c":
    raise SystemExit("SREV-210 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/dll/guidlg.h":
    raise SystemExit("SREV-210 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "dialog hook boundary and fallback behavior",
    "generated standard and extended template rewrite helper",
    "official template header not local array capacity",
    "one dialog-class slot plus one slot per control",
    "fails before parsing item classes",
    "passes the original template to user32",
    "releases temporary renamed class and title buffers exactly once",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-210-dialog-template-class-name-capacity.md").read_text()
header = (ROOT / "Sandboxie/core/dll/guidlg.h").read_text()
src = (ROOT / "Sandboxie/core/dll/guidlg.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-210.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef struct {\n    DWORD style;",
    "WORD cDlgItems;",
    "typedef struct {\n    WORD dlgVer;",
    "WORD signature;",
    "#define GUI_DLG_CLASS_NAME_CAPACITY 256",
    "#define GUI_DLG_VER 1\n#include \"guidlg.h\"",
    "#define GUI_DLG_VER 2\n#include \"guidlg.h\"",
]:
    require(header + src, term, "dialog template owner shape")

fn = between(
    header,
    "void *GUI_CreateDialogTemplate(\n    DLGTMPL *tmpl)",
    "#endif // GUI_CreateDialogTemplate",
)

for term in [
    "WCHAR *old_clsnm[GUI_DLG_CLASS_NAME_CAPACITY];",
    "WCHAR *new_clsnm[GUI_DLG_CLASS_NAME_CAPACITY];",
    "WCHAR *old_winnm = NULL, *new_winnm = NULL;",
    "if (tmpl->cDlgItems >= GUI_DLG_CLASS_NAME_CAPACITY)\n        return NULL;",
    "memzero(old_clsnm, sizeof(old_clsnm));",
    "memzero(new_clsnm, sizeof(new_clsnm));",
    "old_clsnm[0] = (WCHAR *)ptr;",
    "new_clsnm[0] = Gui_CreateClassNameW(old_clsnm[0]);",
    "if (! new_clsnm[0])\n            goto failed;",
    "old_winnm = (WCHAR *)ptr;",
    "new_winnm = Gui_CreateTitleW(old_winnm);",
    "if (! new_winnm)\n        goto failed;",
    "old_clsnm[i + 1] = (WCHAR *)ptr;",
    "new_clsnm[i + 1] = Gui_CreateClassNameW(old_clsnm[i + 1]);",
    "if (! new_clsnm[i + 1])\n                goto failed;",
    "if (! newTmpl)\n        goto failed;",
    "for (i = 0; i <= tmpl->cDlgItems; ++i) {",
    "if (new_clsnm[i] && old_clsnm[i] != new_clsnm[i])\n            Gui_Free(new_clsnm[i]);",
    "failed:",
    "for (i = 0; i <= tmpl->cDlgItems && i < GUI_DLG_CLASS_NAME_CAPACITY; ++i) {",
    "if (new_winnm && new_winnm != old_winnm)\n        Gui_Free(new_winnm);",
]:
    require(fn, term, "bounded dialog template rewrite")

reject(fn, "WCHAR *old_clsnm[256];", "fixed old class array")
reject(fn, "WCHAR *new_clsnm[256];", "fixed new class array")
reject(fn, "WCHAR *old_winnm, *new_winnm;", "uninitialized title pointers")
reject(fn, "if (! newTmpl)\n        return NULL;", "allocation failure without cleanup")

if not fn.index("if (tmpl->cDlgItems >= GUI_DLG_CLASS_NAME_CAPACITY)") < fn.index("old_clsnm[0]"):
    raise SystemExit("SREV-210 failed: cDlgItems capacity guard appears after class parsing")
if not fn.index("memzero(old_clsnm") < fn.index("new_clsnm[0] = Gui_CreateClassNameW"):
    raise SystemExit("SREV-210 failed: class arrays are not initialized before first allocation")
if not fn.index("if (! newTmpl)") < fn.index("failed:"):
    raise SystemExit("SREV-210 failed: allocation failure does not route to cleanup label")
if not fn.index("return newTmpl;") < fn.index("failed:"):
    raise SystemExit("SREV-210 failed: failure label is not isolated after success return")

for block in [
    between(src, "_FX HWND Gui_CreateDialogIndirectParamAorW", "//---------------------------------------------------------------------------\n// Gui_DialogBoxParamW"),
    between(src, "_FX INT_PTR Gui_DialogBoxIndirectParamAorW", "//---------------------------------------------------------------------------\n// Gui_CreateDialogTemplate"),
]:
    require(block, "void *lpTemplate2 = Gui_CreateDialogTemplate(lpTemplate);", "wrapper rewrite call")
    require(block, "if (lpTemplate2)\n        lpTemplate = lpTemplate2;", "wrapper fail-open fallback")
    require(block, "if (lpTemplate2)\n        Gui_Free(lpTemplate2);", "wrapper rewritten template cleanup")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-210",
    "owner: Sandboxie/core/dll/guidlg.c",
    "implementation: Sandboxie/core/dll/guidlg.h",
    "spec: docs/plan/srev-210-dialog-template-class-name-capacity.md",
    "schema: docs/plan/srev-210-dialog-template-class-name-capacity.schema.json",
    "checker: docs/plan/check-srev-210.py",
    "patched source-level after official dialog-template item-count shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-210 source gate passed")
