#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-296 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-296 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-296-guiprop-nonrudehwnd-setprop-suppression.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-296 failed: schema is not draft-07")
if schema.get("id") != "GUIPROP_NONRUDEHWND_SETPROP_SUPPRESSION":
    raise SystemExit("SREV-296 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guiprop.c":
    raise SystemExit("SREV-296 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "UseNonRudeHwndHack controls the NonRudeHWND SetPropA/W suppression",
    "SetPropA/W reports success without storing the NonRudeHWND property when the policy is enabled",
    "UnrestrictedToken is a broader token/UI-restriction owner in token.c and GuiServer.cpp",
    "the default keeps NonRudeHWND suppression enabled outside app-compartment mode",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guiprop = (ROOT / "Sandboxie/core/dll/guiprop.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
token = (ROOT / "Sandboxie/core/drv/token.c").read_text()
guiserver = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-296-guiprop-nonrudehwnd-setprop-suppression.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-296.md").read_text()

init_start = guiprop.index("_FX BOOLEAN Gui_InitProp(HMODULE module)")
init_end = guiprop.index("SBIEDLL_HOOK_GUI(GetPropA);", init_start)
init_block = guiprop[init_start:init_end]

setprop_start = guiprop.index("_FX BOOL Gui_SetPropW")
setprop_end = guiprop.index("//---------------------------------------------------------------------------\n// Gui_RemovePropW", setprop_start)
setprop_block = guiprop[setprop_start:setprop_end]

for term in [
    "SREV-296: NonRudeHWND SetProp suppression is a narrow fullscreen",
    "compatibility policy. UseNonRudeHwndHack controls whether SetPropA/W",
    "reports success without storing the NonRudeHWND property; UnrestrictedToken",
    "is a broader token/UI-restriction owner in token.c and GuiServer.cpp.",
    "The default keeps this suppression enabled outside app-compartment mode.",
    "Gui_NonRudeHWND_Hack = SbieApi_QueryConfBool(NULL, L\"UseNonRudeHwndHack\", !Dll_CompartmentMode);",
]:
    require(init_block, term, "Gui_InitProp")

for stale in [
    "without UnrestrictedToken=y fulscreen does not work",
    "so unless we are running in appcompartment mode by default we drop that SetProp",
]:
    reject(init_block, stale, "Gui_InitProp comment")

for term in [
    "if (Gui_NonRudeHWND_Hack && ((LONG_PTR)lpString & ~0xFFFF) != 0)",
    "if (_wcsicmp(lpString, L\"NonRudeHWND\") == 0)",
    "if (strcmp(lpString, \"NonRudeHWND\") == 0)",
    "return TRUE;",
    "return __sys_SetPropW(hWnd, lpString, hData);",
    "return __sys_SetPropA(hWnd, lpString, hData);",
]:
    require(setprop_block, term, "Gui_SetPropA/W")

for term in [
    "[UseNonRudeHwndHack]",
    "Description=Enables compatibility hack for NonRudeHWND property to improve fullscreen support. [#4761]",
    "[UnrestrictedToken]",
    "Allows sandboxed process to keep its original security token",
]:
    require(settings, term, "settings")

for term in [
    "Conf_Get_Boolean(proc->box->name, L\"UnrestrictedToken\", 0, FALSE)",
    "return Token_DuplicateToken(TokenObject, proc);",
    "Token_Restrict(OriginalToken, SANDBOX_INERT | DISABLE_MAX_PRIVILEGE, proc);",
]:
    require(token, term, "token owner")

for term in [
    "BOOL ok = FALSE;        // set TRUE to skip UIRestrictions",
    "SbieApi_QueryConfBool(boxname, L\"OriginalToken\", FALSE)",
    "SbieApi_QueryConfBool(boxname, L\"UnrestrictedToken\", FALSE)",
]:
    require(guiserver, term, "GuiServer owner")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUIPROP_NONRUDEHWND_SETPROP_SUPPRESSION",
    "UseNonRudeHwndHack controls the NonRudeHWND SetPropA/W suppression",
    "UnrestrictedToken / OriginalToken policy",
    "Token_DuplicateToken / skip UIRestrictions",
    "No setting default, string comparison, return value, atom replacement, access",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-296: GuiProp NonRudeHWND SetProp Suppression",
    "GUIPROP_NONRUDEHWND_SETPROP_SUPPRESSION",
    "srev-296-guiprop-nonrudehwnd-setprop-suppression.schema.json",
    "Sandboxie/core/dll/guiprop.c",
    "UseNonRudeHwndHack",
    "UnrestrictedToken",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-296 source gate passed")
