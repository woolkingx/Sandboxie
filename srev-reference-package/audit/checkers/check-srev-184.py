#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-184 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-184 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-184 failed: {label}")


schema = json.loads((ROOT / "docs/plan/srev-184-xp-file-open-packet-offset-contract.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-184 failed: schema is not draft-07")
if schema.get("id") != "XP_FILE_OPEN_PACKET_OFFSET_CONTRACT":
    raise SystemExit("SREV-184 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/file_xp.c":
    raise SystemExit("SREV-184 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "file_xp.c owns the 32-bit Windows XP",
    "OPEN_PACKET is a private local layout mirror",
    "Context Type equals IO_TYPE_OPEN_PACKET",
    "CreateOptions 0x20 Options 0x30 and CreateDisposition 0x34",
    "compile-time gates through FIELD_OFFSET",
    "Vista and later use the minifilter route",
    "ACCESS_STATE OriginalDesiredAccess is read",
    "does not change file or device parse-procedure routing",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

file_xp = (ROOT / "Sandboxie/core/drv/file_xp.c").read_text()
file_c = (ROOT / "Sandboxie/core/drv/file.c").read_text()
obj_h = (ROOT / "Sandboxie/core/drv/obj.h").read_text()
spec = (ROOT / "docs/plan/srev-184-xp-file-open-packet-offset-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-184.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#include \"file_xp.c\"",
    "if (Driver_OsVersion < DRIVER_WINDOWS_VISTA)",
    "p_File_Init_2 = File_Init_XpHook;",
    "p_File_Unload_2 = File_Unload_XpHook;",
    "#include \"file_flt.c\"",
]:
    require(file_c, term, "file.c XP/minifilter dispatch")

for term in [
    "OBJ_PARSE_PROC_ARGS",
    "OBJ_CALL_SYSTEM_PARSE_PROC",
    "CALL_PARSE_PROC",
]:
    require(obj_h, term, "obj.h parse-procedure shape")

for term in [
    "typedef struct _OPEN_PACKET",
    "FIELD_OFFSET(OPEN_PACKET, CreateOptions) == 0x20",
    "FIELD_OFFSET(OPEN_PACKET, Options) == 0x30",
    "FIELD_OFFSET(OPEN_PACKET, CreateDisposition) == 0x34",
    "if (Context && ((OPEN_PACKET *)Context)->Type == IO_TYPE_OPEN_PACKET)",
    "MyContext->CreateDisposition =",
    "((OPEN_PACKET *)Context)->CreateDisposition;",
    "MyContext->CreateOptions = ((OPEN_PACKET *)Context)->CreateOptions;",
    "MyContext->Options = ((OPEN_PACKET *)Context)->Options;",
    "MyContext->OriginalDesiredAccess = AccessState->OriginalDesiredAccess;",
    "MyContext->Options & IO_OPEN_TARGET_DIRECTORY",
    "Obj_HookParseProc(File_File_ObjectName",
    "Obj_HookParseProc(File_Device_ObjectName",
    "Process_DisableHookEntry(File_File_JumpStub);",
    "Process_DisableHookEntry(File_Device_JumpStub);",
    "OBJ_CALL_SYSTEM_PARSE_PROC(File_File_NtParseProc);",
    "OBJ_CALL_SYSTEM_PARSE_PROC(File_Device_NtParseProc);",
]:
    require(file_xp, term, "file_xp source")

assert_before(
    file_xp,
    "offset gates before File_CreateMyContext reads OPEN_PACKET",
    "FIELD_OFFSET(OPEN_PACKET, CreateOptions) == 0x20",
    "_FX BOOLEAN File_CreateMyContext",
)

for stale in [
    "in Windows Vista, there are extra eight bytes in the Context",
    "works\n        // for 32-bit Windows Vista, Windows 7, and Windows 8",
    "((UCHAR *)Context) += 8;",
]:
    reject(file_xp, stale, "stale Vista context layout claim")

for term in [
    "FIELD_OFFSET",
    "ACCESS_STATE",
    "OPEN_PACKET",
    "XP/2003",
    "Vista+ uses",
    "IO_OPEN_TARGET_DIRECTORY",
    "Sandboxie/core/drv/file_xp.c",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-184",
    "owner: Sandboxie/core/drv/file_xp.c",
    "spec: docs/plan/srev-184-xp-file-open-packet-offset-contract.md",
    "schema: docs/plan/srev-184-xp-file-open-packet-offset-contract.schema.json",
    "checker: docs/plan/check-srev-184.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-184: XP File Open Packet Offset Contract",
    "XP_FILE_OPEN_PACKET_OFFSET_CONTRACT",
    "Sandboxie/core/drv/file_xp.c",
    "FIELD_OFFSET",
    "CreateOptions",
    "Options",
    "CreateDisposition",
    "IO_OPEN_TARGET_DIRECTORY",
]:
    require(ledger, term, "combined ledger")

print("SREV-184 schema/source gate passed")
