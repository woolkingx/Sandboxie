#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-120 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-120 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-120-terminal-user-token-session-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-120 failed: schema is not draft-07")
if schema.get("id") != "TERMINAL_USER_TOKEN_SESSION_CONTRACT":
    raise SystemExit("SREV-120 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "WTSQueryUserToken is keyed by an explicit Remote Desktop Services SessionId",
    "must forward the caller requested SessionId",
    "validates the full GET_USER_TOKEN_REQ size",
    "requested session equals the SbieApi_QueryProcess caller session",
    "calls WTSQueryUserToken with the validated requested session id",
    "DuplicateHandle and close-handle ownership are unchanged",
]:
    require(contracts, term, "schema")

terminal = (ROOT / "Sandboxie/core/dll/terminal.c").read_text()
wire = (ROOT / "Sandboxie/core/svc/terminalwire.h").read_text()
server = (ROOT / "Sandboxie/core/svc/terminalserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-120-terminal-user-token-session-contract.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagGET_USER_TOKEN_REQ",
    "MSG_HEADER h;",
    "ULONG session_id;",
    "struct tagGET_USER_TOKEN_RPL",
    "void *hToken;",
]:
    require(wire, term, "terminalwire.h")

for term in [
    "_FX BOOL Terminal_WTSQueryUserToken(ULONG SessionId, HANDLE *pToken)",
    "req_len = sizeof(GET_USER_TOKEN_REQ);",
    "req->h.length = req_len;",
    "req->h.msgid = MSGID_TERMINAL_GET_USER_TOKEN;",
    "req->session_id = SessionId;",
    "SbieDll_CallServer((MSG_HEADER *)req)",
    "*pToken = rpl->hToken;",
]:
    require(terminal, term, "terminal.c")

for term in [
    "MSG_HEADER *TerminalServer::GetUserToken(MSG_HEADER *msg)",
    "GET_USER_TOKEN_REQ *req = (GET_USER_TOKEN_REQ *)msg;",
    "if (msg->length != sizeof(GET_USER_TOKEN_REQ))",
    "SbieApi_QueryProcess(idProcess, NULL, NULL, NULL, &session_id)",
    "} else if (req->session_id != session_id) {",
    "err = ERROR_ACCESS_DENIED;",
    "WTSQueryUserToken(req->session_id, &hToken)",
    "SbieApi_Call(API_FILTER_TOKEN, 3, (ULONG_PTR)idProcess, (ULONG_PTR)hToken, (ULONG_PTR)&hFilteredToken)",
    "DuplicateHandle(GetCurrentProcess(), hFilteredToken ? hFilteredToken : hToken, hCallerProcess, &pHandle, TOKEN_ALL_ACCESS, FALSE, 0)",
    "CloseHandle(hToken);",
    "rpl->hToken = pHandle;",
]:
    require(server, term, "terminalserver.cpp")

get_user_token = server[server.index("MSG_HEADER *TerminalServer::GetUserToken"):]
reject(get_user_token, "if (msg->length != sizeof(MSG_HEADER)) {\n\n        err = ERROR_INVALID_PARAMETER;", "old bare header request validation")
reject(get_user_token, "WTSQueryUserToken(session_id, &hToken)", "caller-derived WTSQueryUserToken argument")

for term in [
    "### SREV-120: Terminal User Token Session Contract",
    "TERMINAL_USER_TOKEN_SESSION_CONTRACT",
    "srev-120-terminal-user-token-session-contract.schema.json",
    "Sandboxie/core/dll/terminal.c",
    "Sandboxie/core/svc/terminalwire.h",
    "Sandboxie/core/svc/terminalserver.cpp",
    "WTSQueryUserToken",
    "GET_USER_TOKEN_REQ",
    "req->session_id",
    "ERROR_ACCESS_DENIED",
]:
    require(ledger, term, "ledger")

print("SREV-120 schema/source gate passed")
