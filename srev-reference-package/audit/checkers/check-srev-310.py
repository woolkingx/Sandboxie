#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-310 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-310 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-310-key-zonemap-domains-short-circuit.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-310 failed: schema is not draft-07")
if schema.get("id") != "KEY_ZONEMAP_DOMAINS_SHORT_CIRCUIT":
    raise SystemExit("SREV-310 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key_merge.c":
    raise SystemExit("SREV-310 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_ShouldNotMerge owns only the ZoneMap Domains merge short-circuit decision",
    "ZwEnumerateKey and KEY_NODE_INFORMATION define host registry subkey enumeration shape",
    "SREV-033 owns FILE_CHECK_KEY_EXISTS_REQ byte-counted wire string shape",
    "Only SbieSvc object-not-found or path-not-found status proves sandbox Domains copy-key absence for short-circuiting",
    "Allocation failure while building the service probe must preserve normal merge behavior",
]:
    require(contracts, term, "schema")

merge_src = (ROOT / "Sandboxie/core/dll/key_merge.c").read_text()
filewire = (ROOT / "Sandboxie/core/svc/filewire.h").read_text()
fileserver = (ROOT / "Sandboxie/core/svc/fileserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-310-key-zonemap-domains-short-circuit.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-310.md").read_text()
srev_033 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-033.md").read_text(),
    (ROOT / "docs/plan/srev-033-file-key-exists-wire.md").read_text(),
    (ROOT / "docs/plan/srev-033-file-key-exists-wire.schema.json").read_text(),
])

start = merge_src.index("_FX BOOLEAN Key_ShouldNotMerge(")
end = merge_src.index("// Key_MergeCache", start)
func = merge_src[start:end]

for term in [
    "SREV-310: ZoneMap\\Domains merge short-circuit. This path avoids",
    "repeatedly materializing a very large true-host Domains subtree",
    "when the sandbox has no copy key to merge. SbieSvc owns the box-key",
    "existence probe because in-process NtOpenKey may be brokered by",
    "applications such as Adobe Reader X. Probe failure must preserve",
    "normal merge behavior instead of treating absence as proven.",
    "Software\\\\Microsoft\\\\Windows\\\\CurrentVersion",
    "\\\\Internet Settings\\\\ZoneMap\\\\Domains",
    "_wcsnicmp(ptr, Key_System, 17) == 0",
    "_wcsnicmp(ptr, Key_CurrentUser, Key_CurrentUserLen) == 0",
    "req_len = sizeof(FILE_CHECK_KEY_EXISTS_REQ)\n                + path_len * sizeof(WCHAR);",
    "req = Dll_AllocTemp(req_len);",
    "if (! req)\n            return FALSE;",
    "req->h.length = req_len;",
    "req->h.msgid = MSGID_FILE_CHECK_KEY_EXISTS;",
    "req->KeyPath_len = path_len * sizeof(WCHAR);",
    "rpl = SbieDll_CallServer((MSG_HEADER *)req);",
    "rpl->status == STATUS_OBJECT_NAME_NOT_FOUND",
    "rpl->status == STATUS_OBJECT_PATH_NOT_FOUND",
    "return TRUE;",
    "return FALSE;",
]:
    require(func, term, "Key_ShouldNotMerge")

alloc = func.index("req = Dll_AllocTemp(req_len);")
gate = func.index("if (! req)\n            return FALSE;", alloc)
first_write = func.index("req->h.length = req_len;", alloc)
if not alloc < gate < first_write:
    raise SystemExit("SREV-310 failed: allocation gate must precede request writes")

reject(func, "hack:  there can be a large number of subkeys", "source wording")

for term in [
    "ULONG KeyPath_len;                  // BYTE count",
    "WCHAR KeyPath[1];",
]:
    require(filewire, term, "filewire shape")

for term in [
    "MSG_HEADER *FileServer::CheckKeyExists",
    "FileServer_IsValidWireWString",
    "CheckBoxKeyPath(idProcess, req->KeyPath, L\"\\\\\")",
]:
    require(fileserver, term, "service wire validation")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_ZONEMAP_DOMAINS_SHORT_CIRCUIT",
    "On allocation failure it returns `FALSE`, keeping",
    "No Domains path predicate, HKLM/HKCU split, wire request layout",
]:
    require(spec, term, "spec")

for term in [
    "FILE_CHECK_KEY_EXISTS_REQ.KeyPath_len",
    "count. One sender in `Sandboxie/core/dll/key_merge.c`",
    "KeyPath_len bytes, including trailing NUL WCHAR",
    "docs/plan/check-srev-033.py",
]:
    require(srev_033, term, "SREV-033 adjacency")

for term in [
    "### SREV-310: Key ZoneMap Domains Short-Circuit",
    "KEY_ZONEMAP_DOMAINS_SHORT_CIRCUIT",
    "srev-310-key-zonemap-domains-short-circuit.schema.json",
    "Sandboxie/core/dll/key_merge.c",
    "Key_ShouldNotMerge",
    "FILE_CHECK_KEY_EXISTS_REQ",
    "SREV-033",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-310 source gate passed")
