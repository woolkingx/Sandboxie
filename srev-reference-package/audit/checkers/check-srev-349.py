#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-349 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-349 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-349-gui-clipcursor-reply-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-349 failed: schema is not draft-07")
if schema.get("id") != "GUI_CLIPCURSOR_REPLY_CONTRACT":
    raise SystemExit("SREV-349 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiWire.h":
    raise SystemExit("SREV-349 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "ClipCursor returns a Win32 BOOL",
    "reply first ULONG is transport status",
    "retval must be carried after status",
    "captures retval plus error",
    "returns the brokered retval",
    "DPI awareness context is temporarily applied",
    "Windows runtime proof is still required",
]:
    require(contracts, term, "schema")

wire = (ROOT / "Sandboxie/core/svc/GuiWire.h").read_text()
svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
guimisc = (ROOT / "Sandboxie/core/dll/guimisc.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-349-gui-clipcursor-reply-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-349.md").read_text()

for term in [
    "struct tagGUI_CLIP_CURSOR_REQ",
    "struct tagGUI_CLIP_CURSOR_RPL",
    "ULONG status;",
    "ULONG error;",
    "ULONG retval;",
    "typedef struct tagGUI_CLIP_CURSOR_REQ GUI_CLIP_CURSOR_REQ;",
    "typedef struct tagGUI_CLIP_CURSOR_RPL GUI_CLIP_CURSOR_RPL;",
]:
    require(wire, term, "GuiWire ClipCursor ABI")

rpl_start = wire.index("struct tagGUI_CLIP_CURSOR_RPL")
rpl_end = wire.index("};", rpl_start)
rpl_block = wire[rpl_start:rpl_end]
if not (rpl_block.index("ULONG status;") < rpl_block.index("ULONG error;") < rpl_block.index("ULONG retval;")):
    raise SystemExit("SREV-349 failed: GUI_CLIP_CURSOR_RPL field order is wrong")

clip_start = svc.index("ULONG GuiServer::ClipCursorSlave(")
clip_end = svc.index("//---------------------------------------------------------------------------\n// SetForegroundWindowSlave", clip_start)
clip_slave = svc[clip_start:clip_end]
for term in [
    "GUI_CLIP_CURSOR_REQ *req = (GUI_CLIP_CURSOR_REQ *)args->req_buf;",
    "GUI_CLIP_CURSOR_RPL *rpl = (GUI_CLIP_CURSOR_RPL *)args->rpl_buf;",
    "DPI_AWARENESS_CONTEXT old_trd_dpi_ctx",
    "__sys_SetThreadDpiAwarenessContext((DPI_AWARENESS_CONTEXT)(LONG_PTR)req->dpi_awareness_ctx)",
    "BOOL retval = ClipCursor(rect);",
    "rpl->status = 0;",
    "rpl->error = retval ? 0 : GetLastError();",
    "rpl->retval = retval ? 1 : 0;",
    "args->rpl_len = sizeof(*rpl);",
    "__sys_SetThreadDpiAwarenessContext(old_trd_dpi_ctx);",
    "return STATUS_SUCCESS;",
]:
    require(clip_slave, term, "ClipCursorSlave")

for term in [
    "ClipCursor(rect); //if (! )",
    "return STATUS_ACCESS_DENIED; // todo: add reply and return ret value",
    "don't issue errors",
]:
    reject(clip_slave, term, "ClipCursor stale TODO")

clip_dll_start = guimisc.index("_FX BOOL Gui_ClipCursor(")
clip_dll_end = guimisc.index("//---------------------------------------------------------------------------\n// Gui_ResetClipCursor", clip_dll_start)
clip_dll = guimisc[clip_dll_start:clip_dll_end]
for term in [
    "GUI_CLIP_CURSOR_REQ req;",
    "GUI_CLIP_CURSOR_RPL *rpl;",
    "ULONG error;",
    "BOOL retval;",
    "req.msgid = GUI_CLIP_CURSOR;",
    "Gui_ClipCursorActive = TRUE;",
    "Gui_ClipCursorActive = FALSE;",
    "req.dpi_awareness_ctx = __sys_GetThreadDpiAwarenessContext ?",
    "rpl = Gui_CallProxy(&req, sizeof(req), sizeof(*rpl));",
    "retval = rpl->retval;",
    "error = rpl->error;",
    "retval = FALSE;",
    "error = ERROR_ACCESS_DENIED;",
    "SetLastError(error);",
    "return retval;",
]:
    require(clip_dll, term, "Gui_ClipCursor DLL")

for term in [
    "if (data_len >= sizeof(ULONG) && *(ULONG *)data)",
    "status = *(ULONG *)data;",
    "else if (data_len >= rpl_min_len)",
]:
    require(gui, term, "Gui_CallProxy first-field status behavior")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "returning nonzero on success and zero on",
    "`GetLastError`",
    "`WINSTA_WRITEATTRIBUTES`",
    "reply cannot put the Win32 `BOOL` return value in the",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-349: GUI ClipCursor Reply Contract",
    "GUI_CLIPCURSOR_REPLY_CONTRACT",
    "srev-349-gui-clipcursor-reply-contract.schema.json",
    "Sandboxie/core/svc/GuiWire.h",
    "GUI_CLIP_CURSOR_RPL",
    "ClipCursorSlave",
    "Gui_ClipCursor",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-349 source gate passed")
