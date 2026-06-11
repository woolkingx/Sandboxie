#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-224 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-224 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-224-terminal-get-name-reply-terminator.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-224 failed: schema is not draft-07")
if schema.get("id") != "TERMINAL_GET_NAME_REPLY_TERMINATOR":
    raise SystemExit("SREV-224 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "terminalserver.h declares the TerminalServer broker entry points",
    "TERMINAL_GET_NAME_RPL name as a fixed 128 WCHAR reply string",
    "NUL terminated inside rpl name",
    "wcscpy, so the reply buffer owns the termination gate",
    "does not copy uninitialized stack tail bytes",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-224-terminal-get-name-reply-terminator.md").read_text()
ledger = read_combined_ledger(ROOT)
terminal_h = (ROOT / "Sandboxie/core/svc/terminalserver.h").read_text()
wire_h = (ROOT / "Sandboxie/core/svc/terminalwire.h").read_text()
server_cpp = (ROOT / "Sandboxie/core/svc/terminalserver.cpp").read_text()
terminal_c = (ROOT / "Sandboxie/core/dll/terminal.c").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(terminal_h, "MSG_HEADER *GetName(MSG_HEADER *msg);", "terminalserver.h declaration")
require(wire_h, "WCHAR name[128];", "terminalwire fixed reply field")

get_name = server_cpp[
    server_cpp.index("MSG_HEADER *TerminalServer::GetName"):
    server_cpp.index("// GetProperty", server_cpp.index("MSG_HEADER *TerminalServer::GetName"))
]
for term in [
    "WCHAR name[128];\n    memzero(name, sizeof(name));",
    "pWinStationNameFromLogonId(",
    "rpl = (TERMINAL_GET_NAME_RPL *)LONG_REPLY(rpl_len);",
    "memzero(rpl->name, sizeof(rpl->name));",
    "wmemcpy(rpl->name, name, 127);",
    "rpl->name[127] = L'\\0';",
]:
    require(get_name, term, "TerminalServer::GetName source shape")
reject(get_name, "name[120] = L'\\0';", "old stack-buffer terminator")
reject(get_name, "wmemcpy(rpl->name, name, 120);", "old partial reply copy")

client = terminal_c[
    terminal_c.index("_FX BOOLEAN Terminal_WinStationNameFromLogonIdW"):
    terminal_c.index("// Terminal_WinStationGetConnectionProperty", terminal_c.index("_FX BOOLEAN Terminal_WinStationNameFromLogonIdW"))
]
for term in [
    "TERMINAL_GET_NAME_REQ req;",
    "TERMINAL_GET_NAME_RPL *rpl;",
    "req.h.length = sizeof(TERMINAL_GET_NAME_REQ);",
    "req.h.msgid = MSGID_TERMINAL_GET_NAME;",
    "wcscpy(Name, rpl->name);",
]:
    require(client, term, "terminal.c client consumer")

for term in [
    "### SREV-224: Terminal GetName Reply Terminator",
    "TERMINAL_GET_NAME_REPLY_TERMINATOR",
    "srev-224-terminal-get-name-reply-terminator.schema.json",
    "Sandboxie/core/svc/terminalserver.h",
    "Sandboxie/core/svc/terminalserver.cpp",
    "Sandboxie/core/svc/terminalwire.h",
    "Sandboxie/core/dll/terminal.c",
    "rpl->name[127]",
]:
    require(ledger, term, "ledger")

print("SREV-224 source gate passed")
