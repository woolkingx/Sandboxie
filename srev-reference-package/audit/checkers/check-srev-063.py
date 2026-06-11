#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-063 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-063-gui-set-window-long-stub-parser.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-063 failed: schema is not draft-07")
if schema.get("id") != "GUI_SET_WINDOW_LONG_STUB_PARSER":
    raise SystemExit("SREV-063 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "entry byte layout is not a Win32 API contract",
    "A-side parser accepts only 41 B9 01 00 00 00 E9 followed by rel32",
    "W-side parser accepts only 45 33 C9 E9 followed by rel32",
    "A-side branch displacement may be read only after the full A-side prefix",
    "installed only after schema-valid target derivation",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/guiprop.c").read_text()
spec = (ROOT / "docs/plan/srev-063-gui-set-window-long-stub-parser.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX BOOLEAN Gui_Hook_SetWindowLong8(")
end = src.index("// Gui_SetWindowLongPtr8", start)
set_long = src[start:end]

start = src.index("_FX BOOLEAN Gui_Hook_SetWindowLongPtr8(")
end = src.index("// End 64-bit Get/SetWindowLongPtr functions", start)
set_long_ptr = src[start:end]

for label, func in [
    ("Gui_Hook_SetWindowLong8", set_long),
    ("Gui_Hook_SetWindowLongPtr8", set_long_ptr),
]:
    for term in [
        "*(ULONG *)a == 0x0001B941 &&",
        "*(USHORT *)(a + 4) == 0x0000 && a[6] == 0xE9 &&",
        "*(ULONG *)w == 0xE9C93345",
        "LONG a_offset = *(LONG *)(a + 7);",
    ]:
        require(func, term, label)

require(
    set_long,
    "else if (*(ULONG *)a == 0x0001B941 &&\n            *(USHORT *)(a + 4) == 0x0000 && a[6] == 0xE9)",
    "SetWindowLong Windows 10 fallback",
)

for stale in [
    "if (*(ULONG *)a == 0x0001B941 && *(ULONG *)w == 0xE9C93345)",
    "else if (*(ULONG *)a == 0x0001B941) {",
]:
    if stale in set_long or stale in set_long_ptr:
        raise SystemExit(f"SREV-063 failed: stale partial A-side gate remains: {stale}")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlonga",
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptra",
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptrw",
    "srev-063-gui-set-window-long-stub-parser.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-063: GUI SetWindowLong Stub Parser Boundary",
    "GUI_SET_WINDOW_LONG_STUB_PARSER",
    "srev-063-gui-set-window-long-stub-parser.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-063 schema/source gate passed")
