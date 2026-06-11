#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-145 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-145 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-145-gui-async-message-return-abi.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-145 failed: schema is not draft-07")
if schema.get("id") != "GUI_ASYNC_MESSAGE_RETURN_ABI":
    raise SystemExit("SREV-145 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "gui_p.h owns the private User32 function-pointer return ABI used by the GUI hook surface",
    "PostMessageA/W and SendNotifyMessageA/W return BOOL, not LRESULT",
    "PeekMessageA/W and GetMessageA/W return BOOL, not LRESULT",
    "MessageBoxW and MessageBoxExW return int, not LRESULT",
    "PostThreadMessageA/W already returns BOOL, and DispatchMessageA/W remains LRESULT",
    "Hook wrappers that replace PostMessageA/W and SendNotifyMessageA/W must expose the same BOOL return shape as the APIs they replace",
    "The shared Gui_SendPostMessageCommon internal route may keep LRESULT because it also serves SendMessage and SendMessageTimeout paths",
]:
    require(contracts, term, "schema")

gui_p = (ROOT / "Sandboxie/core/dll/gui_p.h").read_text()
guimsg = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
gui_c = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-145-gui-async-message-return-abi.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-145.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef BOOL (*P_SendNotifyMessage)(",
    "typedef BOOL (*P_PostMessage)(",
    "typedef BOOL (*P_PostThreadMessage)(",
    "typedef LRESULT (*P_DispatchMessage)(const MSG *lpmsg);",
    "typedef LRESULT (*P_DispatchMessage8)(const MSG *lpmsg, ULONG IsAscii);",
    "typedef BOOL (*P_PeekMessage)(",
    "typedef BOOL (*P_GetMessage)(",
    "typedef int (*P_MessageBoxW)(",
    "typedef int (*P_MessageBoxExW)(",
    "GUI_SYS_VAR_2(SendNotifyMessage)",
    "GUI_SYS_VAR_2(PostMessage)",
    "extern  P_PeekMessage               __sys_PeekMessageW;",
    "extern  P_MessageBoxW               __sys_MessageBoxW;",
    "extern  P_MessageBoxExW             __sys_MessageBoxExW;",
]:
    require(gui_p, term, "gui_p.h return ABI")

for stale in [
    "typedef LRESULT (*P_SendNotifyMessage)(",
    "typedef LRESULT (*P_PostMessage)(",
    "typedef LRESULT (*P_PeekMessage)(",
    "typedef LRESULT (*P_GetMessage)(",
    "typedef LRESULT (*P_MessageBoxW)(",
    "typedef LRESULT (*P_MessageBoxExW)(",
]:
    reject(gui_p, stale, "stale gui_p.h return ABI")

for term in [
    "static BOOL Gui_SendNotifyMessageA(",
    "static BOOL Gui_SendNotifyMessageW(",
    "static BOOL Gui_PostMessageA(",
    "static BOOL Gui_PostMessageW(",
    "_FX BOOL Gui_SendNotifyMessageA(",
    "_FX BOOL Gui_SendNotifyMessageW(",
    "_FX BOOL Gui_PostMessageA(",
    "_FX BOOL Gui_PostMessageW(",
    "return (BOOL)Gui_SendPostMessageCommon(\n                    'snma'",
    "return (BOOL)Gui_SendPostMessageCommon(\n                    'snmw'",
    "_FX LRESULT Gui_SendPostMessageCommon(",
    "return __sys_PostMessageW(hWnd, uMsg, wParam, lParam);",
    "return __sys_PostMessageA(hWnd, uMsg, wParam, lParam);",
]:
    require(guimsg, term, "guimsg.c wrapper return ABI")

for stale in [
    "static LRESULT Gui_SendNotifyMessageA(",
    "static LRESULT Gui_SendNotifyMessageW(",
    "static LRESULT Gui_PostMessageA(",
    "static LRESULT Gui_PostMessageW(",
    "_FX LRESULT Gui_SendNotifyMessageA(",
    "_FX LRESULT Gui_SendNotifyMessageW(",
    "_FX LRESULT Gui_PostMessageA(",
    "_FX LRESULT Gui_PostMessageW(",
]:
    reject(guimsg, stale, "stale guimsg.c wrapper return ABI")

for term in [
    "P_PeekMessage               __sys_PeekMessageA              = NULL;",
    "P_MessageBoxW               __sys_MessageBoxW               = NULL;",
    "P_MessageBoxExW             __sys_MessageBoxExW             = NULL;",
    "static int Gui_MessageBoxW(",
    "static int Gui_MessageBoxExW(",
    "_FX int Gui_MessageBoxW(",
    "_FX int Gui_MessageBoxExW(",
]:
    require(gui_c, term, "gui.c import/wrapper preservation")

for term in [
    "Sandboxie/core/dll/gui_p.h",
    "Sandboxie/core/dll/guimsg.c",
    "Sandboxie/core/dll/gui.c",
    "### SREV-145: GUI Async Message Return ABI",
    "GUI_ASYNC_MESSAGE_RETURN_ABI",
    "srev-145-gui-async-message-return-abi.schema.json",
    "P_PostMessage",
    "P_SendNotifyMessage",
    "P_PeekMessage",
    "P_MessageBoxW",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-145 schema/source gate passed")
