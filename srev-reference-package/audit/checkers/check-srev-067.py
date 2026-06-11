#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-067 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-067-secure-uac-packet-input-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-067 failed: schema is not draft-07")
if schema.get("id") != "SECURE_UAC_PACKET_INPUT_GATE":
    raise SystemExit("SREV-067 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "wcslen requires a null-terminated wide-character string input",
    "wmemcpy requires valid source and destination buffers",
    "all three packet string pointers are non-null",
    "Dll_Alloc returns a non-null packet buffer",
    "fail closed before global elevation state is set",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
spec = (ROOT / "docs/plan/srev-067-secure-uac-packet-input-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

check_start = src.index("ALIGNED BOOLEAN __cdecl Secure_CheckElevation")
check_end = src.index("// Secure_HandleElevation", check_start)
check_func = src[check_start:check_end]

handle_start = src.index("ALIGNED ULONG_PTR __cdecl Secure_HandleElevation")
handle_end = src.index("// Secure_RpcAsyncCompleteCall", handle_start)
handle_func = src[handle_start:handle_end]

for term in [
    "if (! Args->u.Args1.ProcessHandle)",
    "if (! Args->u.Args1.ApplicationName ||\n                    ! Args->u.Args1.CommandLine ||\n                    ! Args->u.Args1.CurrentDirectory)\n                __leave;",
    "Secure_Elevation_Type = 1;",
]:
    require(check_func, term, "Secure_CheckElevation source")

if check_func.index("! Args->u.Args1.ApplicationName") > check_func.index("Secure_Elevation_Type = 1;"):
    raise SystemExit("SREV-067 failed: type 1 string gate appears after elevation type assignment")

for term in [
    "app_len = wcslen(ApplicationName);",
    "cmd_len = wcslen(CommandLine);",
    "dir_len = wcslen(CurrentDirectory);",
    "pkt = Dll_Alloc(pkt_len);\n    if (! pkt)\n        return 0;",
    "pkt->tzuk = tzuk;",
    "wmemcpy(ptr, ApplicationName, app_len);",
    "wmemcpy(ptr, CommandLine, cmd_len);",
    "wmemcpy(ptr, CurrentDirectory, dir_len);",
]:
    require(handle_func, term, "Secure_HandleElevation source")

if handle_func.index("if (! pkt)") > handle_func.index("pkt->tzuk = tzuk;"):
    raise SystemExit("SREV-067 failed: allocation gate appears after packet write")

for term in [
    "https://learn.microsoft.com/en-us/previous-versions/windows/embedded/ms860442%28v%3Dmsdn.10%29",
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-170",
    "srev-067-secure-uac-packet-input-gate.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-067: Secure UAC Packet Input Gate",
    "SECURE_UAC_PACKET_INPUT_GATE",
    "srev-067-secure-uac-packet-input-gate.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-067 schema/source gate passed")
