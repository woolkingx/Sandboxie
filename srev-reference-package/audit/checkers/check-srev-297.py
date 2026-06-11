#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-297 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-297 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-297-guiprop-setwindowlong-stub-opcode-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-297 failed: schema is not draft-07")
if schema.get("id") != "GUIPROP_SETWINDOWLONG_STUB_OPCODE_COMMENT":
    raise SystemExit("SREV-297 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guiprop.c":
    raise SystemExit("SREV-297 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "SREV-063 owns SetWindowLong8 and SetWindowLongPtr8 stub parser behavior",
    "the source opcode comments use rel32 parser terms",
    "SetWindowLong export executable bytes are a Sandboxie-local compatibility schema not a Microsoft API contract",
    "unknown SetWindowLong stub layouts still fail initialization",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guiprop = (ROOT / "Sandboxie/core/dll/guiprop.c").read_text()
spec = (ROOT / "docs/plan/srev-297-guiprop-setwindowlong-stub-opcode-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-297.md").read_text()
srev_063 = (ROOT / "docs/plan/ledger/srev-063.md").read_text()

start = guiprop.index("_FX BOOLEAN Gui_Hook_SetWindowLong8(HMODULE module)")
end = guiprop.index("// Gui_SetWindowLongPtr8", start)
set_long = guiprop[start:end]

start = guiprop.index("_FX BOOLEAN Gui_Hook_SetWindowLongPtr8(HMODULE module)")
end = guiprop.index("// End 64-bit Get/SetWindowLongPtr functions", start)
set_long_ptr = guiprop[start:end]

for label, func, a_name, w_name in [
    ("Gui_Hook_SetWindowLong8", set_long, "SetWindowLongA", "SetWindowLongW"),
    ("Gui_Hook_SetWindowLongPtr8", set_long_ptr, "SetWindowLongPtrA", "SetWindowLongPtrW"),
]:
    for term in [
        "SREV-297: opcode comments use parser terms from SREV-063.",
        f"{a_name}",
        "(11 bytes)      jmp rel32           E9 xx xx xx xx",
        f"{w_name}",
        "(8 bytes)       jmp rel32           E9 xx xx xx xx",
        "*(ULONG *)a == 0x0001B941 &&",
        "*(USHORT *)(a + 4) == 0x0000 && a[6] == 0xE9 &&",
        "*(ULONG *)w == 0xE9C93345",
        "LONG a_offset = *(LONG *)(a + 7);",
        "LONG w_offset = *(LONG *)(w + 4);",
    ]:
        require(func, term, label)
    reject(func, "jmp xxx", label)

require(
    set_long,
    "else if (*(ULONG *)a == 0x0001B941 &&\n            *(USHORT *)(a + 4) == 0x0000 && a[6] == 0xE9)",
    "SetWindowLong Windows 10 fallback",
)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUIPROP_SETWINDOWLONG_STUB_OPCODE_COMMENT",
    "rel32",
    "SREV-063",
    "Sandboxie-local compatibility schema",
    "no parser behavior change",
]:
    require(spec, term, "spec")

for term in [
    "GUI_SET_WINDOW_LONG_STUB_PARSER",
    "41 B9 01 00 00 00 E9 rel32",
    "45 33 C9 E9 rel32",
    "unknown A-side layouts fail initialization",
]:
    require(srev_063, term, "SREV-063 adjacency")

for term in [
    "### SREV-297: GuiProp SetWindowLong Stub Opcode Comment",
    "GUIPROP_SETWINDOWLONG_STUB_OPCODE_COMMENT",
    "srev-297-guiprop-setwindowlong-stub-opcode-comment.schema.json",
    "Sandboxie/core/dll/guiprop.c",
    "Gui_Hook_SetWindowLong8",
    "Gui_Hook_SetWindowLongPtr8",
    "SREV-063",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-297 source gate passed")
