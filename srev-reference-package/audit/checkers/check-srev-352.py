#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-352 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-352 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-352-sbieini-get-dat-reserved-wire-surface.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-352 failed: schema is not draft-07")
if schema.get("id") != "SBIEINI_GET_DAT_RESERVED_WIRE_SURFACE":
    raise SystemExit("SREV-352 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/sbieiniserver.cpp":
    raise SystemExit("SREV-352 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "MSGID_SBIE_INI_SET_DAT remains the active Sandboxie home-directory dat write/delete route",
    "MSGID_SBIE_INI_GET_DAT remains reserved and unrouted until a read reply schema exists",
    "sbieiniwire.h currently has no dat-file read reply shape with file size byte count or partial-read contract",
    "SetDatFile remains gated to the session leader and to terminated *.dat names without parent traversal",
    "a future GET_DAT route must define max read size EOF behavior reply buffer shape and caller authorization before code is wired",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/sbieiniserver.cpp").read_text()
header = (ROOT / "Sandboxie/core/svc/sbieiniserver.h").read_text()
wire = (ROOT / "Sandboxie/core/svc/sbieiniwire.h").read_text()
msgids = (ROOT / "Sandboxie/core/svc/msgids.h").read_text()
callsvc = (ROOT / "Sandboxie/core/dll/callsvc.c").read_text()
control = (ROOT / "Sandboxie/apps/control/SbieIni.cpp").read_text()
spec = (ROOT / "docs/plan/srev-352-sbieini-get-dat-reserved-wire-surface.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-352.md").read_text()

handler_start = svc.index("MSG_HEADER *SbieIniServer::Handler2(")
handler_end = svc.index("//---------------------------------------------------------------------------\n// GetVersion", handler_start)
handler = svc[handler_start:handler_end]

set_start = svc.index("MSG_HEADER *SbieIniServer::SetDatFile(")
set_end = svc.index("//---------------------------------------------------------------------------\n// Reserved GetDatFile wire surface", set_start)
set_block = svc[set_start:set_end]

reserved_start = svc.index("// Reserved GetDatFile wire surface")
reserved_end = svc.index("//---------------------------------------------------------------------------\n// RC4Crypt", reserved_start)
reserved_block = svc[reserved_start:reserved_end]

for term in [
    "MSGID_SBIE_INI_SET_DAT",
    "return SetDatFile(msg, idProcess);",
    "SREV-352: MSGID_SBIE_INI_GET_DAT is a reserved wire id.",
    "unrouted until a read reply schema",
    "length cap, file-size gate, and",
    "authorization model are defined",
]:
    require(handler, term, "Handler2 dat routing")

if re.search(r"^[ \t]*if\s*\(\s*msg->msgid\s*==\s*MSGID_SBIE_INI_GET_DAT\s*\)", handler, re.MULTILINE):
    raise SystemExit("SREV-352 failed: active GET_DAT handler route exists")

for term in [
    "SREV-352: SET_DAT has a session-leader write/delete owner.",
    "GET_DAT remains",
    "read path needs its own reply schema and file-size gate.",
]:
    require(reserved_block, term, "reserved GetDatFile source comment")

for stale in [
    "ToDo",
    "TODO",
    "todo",
    "MSG_HEADER *SbieIniServer::GetDatFile(MSG_HEADER *msg, HANDLE idProcess)",
]:
    reject(reserved_block, stale, "reserved GetDatFile block")

for term in [
    "SbieApi_SessionLeader(m_session_id, &SessionLeaderPid);",
    "if (SessionLeaderPid != idProcess)",
    "return SHORT_REPLY(STATUS_ACCESS_DENIED);",
    "if (! SbieIni_HasTerminator(req->setting, ARRAYSIZE(req->setting)))",
    "FIELD_OFFSET(SBIE_INI_SETTING_REQ, value)",
    "req->value_len > req->h.length - offset",
    "wcsrchr(req->setting, L'.')",
    "_wcsicmp(ext, L\".dat\") != 0",
    "wcsstr(req->setting, L\"..\") != NULL",
    "STATUS_INVALID_FILE_FOR_SECTION",
    "SbieApi_GetHomePath(path, 768, NULL, 0)",
    "if (req->value_len == 0)",
    "NtDeleteFile(&objattrs);",
    "NtCreateFile(&handle, FILE_GENERIC_WRITE",
    "FILE_OVERWRITE_IF",
    "NtWriteFile(handle, NULL, NULL, NULL, &IoStatusBlock, req->value, req->value_len, NULL, NULL);",
]:
    require(set_block, term, "SetDatFile active route")

for term in [
    "#define MSGID_SBIE_INI_SET_DAT                  0x18D1",
    "#define MSGID_SBIE_INI_GET_DAT                  0x18D2",
]:
    require(msgids, term, "msgids")

for term in [
    "struct tagSBIE_INI_SETTING_REQ",
    "struct tagSBIE_INI_SETTING_RPL",
    "ULONG value_len;",
    "WCHAR value[1];",
]:
    require(wire, term, "wire setting shape")

for stale in [
    "SBIE_INI_GET_DAT_REQ",
    "SBIE_INI_GET_DAT_RPL",
    "tagSBIE_INI_GET_DAT",
]:
    reject(wire, stale, "wire GET_DAT shape")

require(header, "SREV-352: GET_DAT is reserved until a read reply schema and gate exist.", "header reserved comment")
reject(header, "MSG_HEADER *GetDatFile(MSG_HEADER *msg, HANDLE idProcess);", "active header prototype")

for text, label in [(callsvc, "callsvc"), (control, "control")]:
    reject(text, "MSGID_SBIE_INI_GET_DAT", label)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SBIEINI_GET_DAT_RESERVED_WIRE_SURFACE",
    "`MSGID_SBIE_INI_GET_DAT`",
    "reserved wire id",
    "reply schema",
    "file-size gate",
    "authorization model",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-352: SbieIni GET_DAT Reserved Wire Surface",
    "SBIEINI_GET_DAT_RESERVED_WIRE_SURFACE",
    "srev-352-sbieini-get-dat-reserved-wire-surface.schema.json",
    "Sandboxie/core/svc/sbieiniserver.cpp",
    "MSGID_SBIE_INI_GET_DAT",
    "SetDatFile",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-352 source gate passed")
