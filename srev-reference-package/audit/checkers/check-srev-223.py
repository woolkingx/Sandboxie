#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-223 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-223 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-223-is-host-path-final-length.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-223 failed: schema is not draft-07")
if schema.get("id") != "IS_HOST_PATH_FINAL_LENGTH_GATE":
    raise SystemExit("SREV-223 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "misc.h declares service-wide helpers",
    "IsHostPath compares a requested host path",
    "GetFinalPathNameByHandleW returns the final path length",
    "nonzero return smaller than the buffer capacity",
    "use the returned final path length",
    "Device Mup is a network share path",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-223-is-host-path-final-length.md").read_text()
ledger = read_combined_ledger(ROOT)
misc_h = (ROOT / "Sandboxie/core/svc/misc.h").read_text()
main_cpp = (ROOT / "Sandboxie/core/svc/main.cpp").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(misc_h, "bool IsHostPath(HANDLE idProcess, WCHAR* dos_path);", "misc.h declaration")

is_host_path = main_cpp[
    main_cpp.index("bool IsHostPath("):
    main_cpp.index("return result;", main_cpp.index("bool IsHostPath("))
]
for term in [
    "handle = CreateFileW(dos_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);",
    "DWORD dwRet = GetFinalPathNameByHandleW(handle, request_path, len, VOLUME_NAME_NT);",
    "if (dwRet == 0 || dwRet >= len)",
    "const WCHAR MupPrefix[] = L\"\\\\Device\\\\Mup\\\\\";",
    "const ULONG MupPrefixLen = (sizeof(MupPrefix) / sizeof(WCHAR)) - 1;",
    "if (dwRet >= MupPrefixLen && _wcsnicmp(request_path, MupPrefix, MupPrefixLen) == 0)",
    "ULONG request_path_len = dwRet;",
    "SbieApi_QueryProcessPath(idProcess, sandbox_path, NULL, NULL, &len, NULL, NULL)",
]:
    require(is_host_path, term, "IsHostPath source shape")

reject(is_host_path, "if(len > 12 && _wcsnicmp(request_path, L\"\\\\Device\\\\Mup\\\\\", 12) == 0)", "old fixed-capacity MUP gate")
reject(is_host_path, "ULONG request_path_len = wcslen(request_path);", "old unowned final path length")
reject(is_host_path, "dwRet > len", "old too-small-buffer gate")

for term in [
    "### SREV-223: IsHostPath Final Path Length Gate",
    "IS_HOST_PATH_FINAL_LENGTH_GATE",
    "srev-223-is-host-path-final-length.schema.json",
    "Sandboxie/core/svc/misc.h",
    "Sandboxie/core/svc/main.cpp",
    "GetFinalPathNameByHandleW",
    "IsHostPath",
    "MupPrefixLen",
]:
    require(ledger, term, "ledger")

print("SREV-223 source gate passed")
