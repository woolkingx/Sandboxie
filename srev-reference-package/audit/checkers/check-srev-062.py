#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-062 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-062-gui-dispatch-message-stub-parser.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-062 failed: schema is not draft-07")
if schema.get("id") != "GUI_DISPATCH_MESSAGE_STUB_PARSER":
    raise SystemExit("SREV-062 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "entry byte layout is not a Win32 API contract",
    "A-stub parser accepts only BA 01 00 00 00 followed by EB rel8 or E9 rel32",
    "W-stub parser accepts only 33 D2 followed by EB rel8 or E9 rel32",
    "Unknown A-side or W-side opcodes must fail closed",
    "installed only when the A-side and W-side derived targets are equal",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
spec = (ROOT / "docs/plan/srev-062-gui-dispatch-message-stub-parser.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX BOOLEAN Gui_Hook_DispatchMessage8(")
end = src.index("#endif\n\n#endif _WIN64", start)
func = src[start:end]

for term in [
    "LONG  a_offset = 0;",
    "LONG  w_offset = 0;",
    "if (a[5] == 0xEB)",
    "else if (a[5] == 0xE9)",
    "else\n            return FALSE;",
    "if (w[2] == 0xEB)",
    "else if (w[2] == 0xE9)",
    "if ((a + a_offset) == (w + w_offset))",
    "__sys_DispatchMessage8 = (P_DispatchMessage8)(w + w_offset);",
]:
    require(func, term, "Gui_Hook_DispatchMessage8 source")

if "else\n            w_offset = 0;" in func:
    raise SystemExit("SREV-062 failed: unknown W-side opcode still continues as offset zero")

if func.count("else\n            return FALSE;") < 2:
    raise SystemExit("SREV-062 failed: both A-side and W-side unknown opcodes must fail closed")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagea",
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagew",
    "https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress",
    "srev-062-gui-dispatch-message-stub-parser.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-062: GUI DispatchMessage Stub Parser Boundary",
    "GUI_DISPATCH_MESSAGE_STUB_PARSER",
    "srev-062-gui-dispatch-message-stub-parser.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-062 schema/source gate passed")
