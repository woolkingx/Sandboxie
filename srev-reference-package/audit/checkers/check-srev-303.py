#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-303 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-303 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-303-key-wow64-service-request-allocation-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-303 failed: schema is not draft-07")
if schema.get("id") != "KEY_WOW64_SERVICE_REQUEST_ALLOCATION_GATE":
    raise SystemExit("SREV-303 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-303 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_FixNameWow64 owns the 64-bit caller KEY_WOW64_32KEY service-assisted route",
    "Key_FixNameWow64_2 must prove FILE_OPEN_WOW64_KEY_REQ allocation before writing the request",
    "filewire.h owns the FILE_OPEN_WOW64_KEY_REQ byte-counted key path shape",
    "FileServer::OpenWow64Key owns the server-side RegOpenKeyEx KEY_WOW64_32KEY operation",
    "SREV-303 does not change WOW64 flag semantics or duplicate Wow6432Node cleanup",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
filewire = (ROOT / "Sandboxie/core/svc/filewire.h").read_text()
fileserver = (ROOT / "Sandboxie/core/svc/fileserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-303-key-wow64-service-request-allocation-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-303.md").read_text()

start = key.index("_FX NTSTATUS Key_FixNameWow64(")
end = key.index("// Key_GetWow64Flag", start)
funcs = key[start:end]

for term in [
    "if (! (DesiredAccess & KEY_WOW64_32KEY))\n            return STATUS_SUCCESS;",
    "SREV-303: a 64-bit process requesting KEY_WOW64_32KEY needs",
    "the service-assisted RegOpenKeyEx path because there is no",
    "WOW64 NtOpenKey thunk to rewrite this native call locally.",
    "return Key_FixNameWow64_2(OutTruePath, OutCopyPath);",
    "req_len = sizeof(FILE_OPEN_WOW64_KEY_REQ) + TruePath_len;",
    "req = (FILE_OPEN_WOW64_KEY_REQ *)Dll_AllocTemp(req_len);",
    "if (! req)\n        return STATUS_INSUFFICIENT_RESOURCES;",
    "req->h.length = req_len;",
    "req->h.msgid = MSGID_FILE_OPEN_WOW64_KEY;",
    "req->Wow64DesiredAccess = KEY_WOW64_32KEY;",
    "req->KeyPath_len = TruePath_len;",
    "memcpy(req->KeyPath, TruePath, TruePath_len);",
    "SbieDll_CallServer((MSG_HEADER *)req)",
]:
    require(funcs, term, "key.c")

if funcs.index("if (! req)") > funcs.index("req->h.length = req_len;"):
    raise SystemExit("SREV-303 failed: allocation gate must precede request writes")

for stale in [
    "ToDo: ???",
    "NoSysCallHooks BEGIN",
    "NoSysCallHooks END",
    "SbieApi_QueryConfBool(NULL, L\"NoSysCallHooks\", FALSE)",
]:
    reject(funcs, stale, "source wording")

for term in [
    "struct tagFILE_OPEN_WOW64_KEY_REQ",
    "ULONG Wow64DesiredAccess;           // KEY_WOW64_32KEY or KEY_WOW64_64KEY",
    "ULONG KeyPath_len;                  // BYTE count",
    "WCHAR KeyPath[1];",
]:
    require(filewire, term, "filewire")

for term in [
    "MSG_HEADER *FileServer::OpenWow64Key(MSG_HEADER *msg, HANDLE idProcess)",
    "FILE_OPEN_WOW64_KEY_REQ *req = (FILE_OPEN_WOW64_KEY_REQ *)msg;",
    "FileServer_IsValidWireWString(",
    "if (req->Wow64DesiredAccess != KEY_WOW64_32KEY)",
    "RegOpenKeyEx(hRootKey, lpSubKey, 0,\n                          KEY_READ | KEY_WOW64_32KEY, &hKey);",
]:
    require(fileserver, term, "fileserver")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_WOW64_SERVICE_REQUEST_ALLOCATION_GATE",
    "64-bit process that explicitly requests `KEY_WOW64_32KEY`",
    "No WOW64 flag semantics, `FILE_OPEN_WOW64_KEY_REQ` layout",
    "STATUS_INSUFFICIENT_RESOURCES",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-303: Key WOW64 Service Request Allocation Gate",
    "KEY_WOW64_SERVICE_REQUEST_ALLOCATION_GATE",
    "srev-303-key-wow64-service-request-allocation-gate.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_FixNameWow64",
    "FILE_OPEN_WOW64_KEY_REQ",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-303 source gate passed")
