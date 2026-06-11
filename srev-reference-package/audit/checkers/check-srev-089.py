#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-089 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-089-guihook-wisptis-fake-hook-handle.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-089 failed: schema is not draft-07")
if schema.get("id") != "GUIHOOK_WISPTIS_FAKE_HOOK_HANDLE":
    raise SystemExit("SREV-089 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "WISPTIS WH_MOUSE_LL",
    "owner-local cookie address",
    "before pointer-shape probing",
    "real HHOOK values still forward",
    "GUI_HOOK pointer handles",
    "does not broaden WISPTIS",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/guihook.c").read_text()
spec = (ROOT / "docs/plan/srev-089-guihook-wisptis-fake-hook-handle.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "static UCHAR Gui_WisptisBlockedHook;",
    "if (idHook == WH_MOUSE_LL && Dll_ImageType == DLL_IMAGE_WISPTIS)",
    "WISPTIS low-level mouse hook is locally suppressed.",
    "hhook = (HHOOK)&Gui_WisptisBlockedHook;",
    "if (hhk == (HHOOK)&Gui_WisptisBlockedHook)",
    "return TRUE;",
]:
    require(src, term, "guihook.c fake WISPTIS hook owner path")

if "(HHOOK)(ULONG_PTR)0x12345678" in src:
    raise SystemExit("SREV-089 failed: stale magic fake HHOOK remains")
if "hack:  block hook by Microsoft WISPTIS" in src:
    raise SystemExit("SREV-089 failed: stale hack comment remains")

cookie_index = src.index("if (hhk == (HHOOK)&Gui_WisptisBlockedHook)")
align_index = src.index("#ifdef _WIN64", src.index("if (!hhk)"))
if cookie_index > align_index:
    raise SystemExit("SREV-089 failed: fake cookie check must precede pointer probing")

for term in [
    "return __sys_UnhookWindowsHookEx(hhk);",
    "ghk = (GUI_HOOK *) hhk;",
    "ghk->eyecatcher != tzuk",
    "__sys_UnhookWindowsHookEx(thd->hhk);",
]:
    require(src, term, "guihook.c existing real/pseudo-global unhook paths")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-089: GUI Hook WISPTIS Fake Hook Handle",
    "GUIHOOK_WISPTIS_FAKE_HOOK_HANDLE",
    "srev-089-guihook-wisptis-fake-hook-handle.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-089 schema/source gate passed")
