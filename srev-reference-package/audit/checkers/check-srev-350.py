#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-350 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-350 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-350-gui-sendpost-system-message-policy-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-350 failed: schema is not draft-07")
if schema.get("id") != "GUI_SENDPOST_SYSTEM_MESSAGE_POLICY_COMMENT":
    raise SystemExit("SREV-350 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiServer.cpp":
    raise SystemExit("SREV-350 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "cross-sandbox send/post message policy decision",
    "Input-shaped messages are allowed",
    "lifecycle shutdown notification or shell-control semantics",
    "Explorer WM_USER class exceptions",
    "changes comments and proof only",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-350-gui-sendpost-system-message-policy-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-350.md").read_text()

allow_start = svc.index("bool GuiServer::AllowSendPostMessage(")
allow_end = svc.index("//---------------------------------------------------------------------------\n// RunConsoleSlave", allow_start)
allow = svc[allow_start:allow_end]

for term in [
    "if (ProcessFlags & SBIE_FLAG_OPEN_ALL_WIN_CLASS)",
    "#define IS_INPUT_MESSAGE(msg)",
    "if (IS_INPUT_MESSAGE(msg))",
    "SREV-350: deny cross-sandbox lifecycle, shutdown, notification, and",
    "shell-control system messages before they reach windows outside the",
    "WM_QUERYENDSESSION carry process/session semantics beyond ordinary UI",
    "static const ULONG sysmsgs[] = {",
    "0x0002,             // WM_DESTROY",
    "0x000B,             // WM_SETREDRAW",
    "0x0010,             // WM_CLOSE",
    "0x0011,             // WM_QUERYENDSESSION",
    "0x0012,             // WM_QUIT",
    "0x0016,             // WM_ENDSESSION",
    "0x003B,             // ?",
    "0x004E,             // WM_NOTIFY",
    "0x0082,             // WM_NCDESTROY",
    "0x0111,             // WM_COMMAND",
    "0x0112,             // WM_SYSCOMMAND",
    "0x0319,             // WM_APPCOMMAND",
    "0x000F,             // WM_PAINT",
]:
    require(allow, term, "AllowSendPostMessage")

for term in [
    "discard some messages that might hide, close or crash windows",
    "Shell_TrayWnd reacts to it badly",
]:
    reject(allow, term, "stale result-only comment")

for term in [
    "if ((msg >= WM_USER) || IS_INPUT_MESSAGE(msg))",
    "GetWindowThreadProcessId(GetShellWindow(), &pidExplorer)",
    "ISWNDCLASS(18, L\"CicMarshalWndClass\")",
    "ISWNDCLASS(7, L\"Progman\")",
    "ISWNDCLASS(14, L\"MSTaskSwWClass\")",
    "ISWNDCLASS(13, L\"Shell_TrayWnd\")",
    "if (blocked)\n                return false;",
]:
    require(allow, term, "Explorer WM_USER policy adjacency")

send_start = svc.index("ULONG GuiServer::SendPostMessageSlave(")
send_end = svc.index("//---------------------------------------------------------------------------\n// SendCopyDataSlave", send_start)
send_block = svc[send_start:send_end]
for term in [
    "CheckWindowAccessible(args->pid, NULL, list, hwnd)",
    "CompareIntegrityLevels(args->pid, hwnd)",
    "AllowSendPostMessage(args->pid, msg, IsSendMsg, hwnd)",
    "rpl->error = ERROR_INVALID_WINDOW_HANDLE;",
]:
    require(send_block, term, "SendPostMessageSlave policy caller")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "`WM_CLOSE` asks",
    "`WM_QUERYENDSESSION` is part of the system shutdown",
    "`WM_QUIT` is not a window",
    "`WM_SYSCOMMAND` carries",
    "`WM_NOTIFY` carries",
    "Runtime gate: none for this comment-only",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-350: GUI Send/Post System Message Policy Comment",
    "GUI_SENDPOST_SYSTEM_MESSAGE_POLICY_COMMENT",
    "srev-350-gui-sendpost-system-message-policy-comment.schema.json",
    "Sandboxie/core/svc/GuiServer.cpp",
    "AllowSendPostMessage",
    "WM_QUERYENDSESSION",
    "WM_SYSCOMMAND",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-350 source gate passed")
