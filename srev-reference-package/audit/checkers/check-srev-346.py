#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-346 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-346 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-346-gui-clipboard-metafile-policy-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-346 failed: schema is not draft-07")
if schema.get("id") != "GUI_CLIPBOARD_METAFILE_POLICY_GATE":
    raise SystemExit("SREV-346 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiServer.cpp":
    raise SystemExit("SREV-346 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "OpenClipboard is a Sandboxie box policy",
    "GetClipboardDataSlave enforces OpenClipboard before opening the clipboard",
    "GetClipboardMetaFileSlave is a secondary CF_METAFILEPICT read broker",
    "result zero and ERROR_ACCESS_DENIED",
    "must not call OpenClipboard NULL before the policy check passes",
    "CF_METAFILEPICT GetClipboardData GlobalLock GetMetaFileBitsEx section-copy topology",
    "Windows runtime proof is still required",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
guimisc = (ROOT / "Sandboxie/core/dll/guimisc.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
wire = (ROOT / "Sandboxie/core/svc/GuiWire.h").read_text()
spec = (ROOT / "docs/plan/srev-346-gui-clipboard-metafile-policy-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-346.md").read_text()

data_start = svc.index("ULONG GuiServer::GetClipboardDataSlave(")
data_end = svc.index("//---------------------------------------------------------------------------\n// GetClipboardDataSlave2", data_start)
data_block = svc[data_start:data_end]

meta_start = svc.index("ULONG GuiServer::GetClipboardMetaFileSlave(")
meta_end = svc.index("//---------------------------------------------------------------------------\n// SendPostMessageSlave", meta_start)
meta_block = svc[meta_start:meta_end]

for term in [
    "if (!SbieApi_QueryConfBool(boxname, L\"OpenClipboard\", TRUE))",
    "rpl->error = ERROR_ACCESS_DENIED;",
    "goto finish;",
    "if (! OpenClipboard(NULL))",
    "HANDLE mem_handle = GetClipboardData(req->format);",
]:
    require(data_block, term, "GetClipboardDataSlave policy adjacency")

for term in [
    "if (req->format != CF_METAFILEPICT)",
    "rpl->result = 0;",
    "rpl->error = 0;",
    "SREV-346: the metafile helper is a secondary clipboard-read path",
    "must inherit the same OpenClipboard policy gate as GetClipboardDataSlave.",
    "WCHAR boxname[BOXNAME_COUNT] = { 0 };",
    "WCHAR exename[99] = { 0 };",
    "SbieApi_QueryProcess((HANDLE)args->pid, boxname, exename, NULL, NULL);",
    "if (!SbieApi_QueryConfBool(boxname, L\"OpenClipboard\", TRUE))",
    "rpl->error = ERROR_ACCESS_DENIED;",
    "goto finish;",
    "EnterCriticalSection(&m_SlavesLock);",
    "if (OpenClipboard(NULL))",
    "HANDLE mem_handle = GetClipboardData(req->format);",
    "METAFILEPICT *mf = (METAFILEPICT *)GlobalLock(mem_handle);",
    "ULONG mem_len = GetMetaFileBitsEx(mf->hMF, 0, NULL);",
    "GetMetaFileBitsEx(mf->hMF, mem_len, mem_ptr)",
    "GetClipboardDataSlave2(",
    "GlobalUnlock(mem_handle);",
    "CloseClipboard();",
    "LeaveCriticalSection(&m_SlavesLock);",
    "finish:",
    "args->rpl_len = sizeof(GUI_GET_CLIPBOARD_DATA_RPL);",
]:
    require(meta_block, term, "GetClipboardMetaFileSlave")

reject(meta_block, "//todo:  fail if the calling process should not have clipboard access", "metafile clipboard TODO")

if meta_block.index("SbieApi_QueryConfBool(boxname, L\"OpenClipboard\", TRUE)") > meta_block.index("OpenClipboard(NULL)"):
    raise SystemExit("SREV-346 failed: policy check occurs after OpenClipboard")
if meta_block.index("goto finish;") > meta_block.index("EnterCriticalSection(&m_SlavesLock);"):
    raise SystemExit("SREV-346 failed: denied path enters clipboard critical section")
if meta_block.index("finish:") < meta_block.index("LeaveCriticalSection(&m_SlavesLock);"):
    raise SystemExit("SREV-346 failed: finish label moved before critical-section release")

for term in [
    "if (!SbieApi_QueryConfBool(NULL, L\"OpenClipboard\", TRUE))",
    "req.msgid = GUI_GET_CLIPBOARD_METAFILE;",
    "req.format = fmt;",
    "Gui_CallProxyEx(&req, sizeof(req), sizeof(*rpl), TRUE);",
    "SetMetaFileBitsEx(",
]:
    require(guimisc, term, "Gui_GetClipboardData_MF adjacency")

for term in [
    "GUI_GET_CLIPBOARD_DATA",
    "GUI_GET_CLIPBOARD_METAFILE",
    "struct tagGUI_GET_CLIPBOARD_DATA_REQ",
    "struct tagGUI_GET_CLIPBOARD_DATA_RPL",
]:
    require(wire, term, "GuiWire clipboard protocol")

for term in [
    "[OpenClipboard]",
    "Description=Controls whether processes in the sandbox can access the system clipboard.",
]:
    require(settings, term, "OpenClipboard setting")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "clipboard as a shared data-transfer facility",
    "`OpenClipboard` opens the",
    "`GetClipboardData` requires a previously opened clipboard",
    "clipboard-owned handle",
    "window station as containing a clipboard",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-346: GUI Clipboard Metafile Policy Gate",
    "GUI_CLIPBOARD_METAFILE_POLICY_GATE",
    "srev-346-gui-clipboard-metafile-policy-gate.schema.json",
    "Sandboxie/core/svc/GuiServer.cpp",
    "GetClipboardMetaFileSlave",
    "OpenClipboard",
    "ERROR_ACCESS_DENIED",
    "CF_METAFILEPICT",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-346 source gate passed")
