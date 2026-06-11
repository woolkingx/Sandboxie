#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-295 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-295 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-295-guimsg-dispatch-stub-opcode-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-295 failed: schema is not draft-07")
if schema.get("id") != "GUIMSG_DISPATCH_STUB_OPCODE_COMMENT":
    raise SystemExit("SREV-295 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guimsg.c":
    raise SystemExit("SREV-295 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "SREV-062 owns DispatchMessage8 stub parser behavior",
    "the source opcode comment uses rel8 and rel32 parser terms",
    "DispatchMessage export executable bytes are a Sandboxie-local compatibility schema not a Microsoft API contract",
    "unknown DispatchMessage stub opcodes still fail closed",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guimsg = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
spec = (ROOT / "docs/plan/srev-295-guimsg-dispatch-stub-opcode-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-295.md").read_text()
srev_062 = (ROOT / "docs/plan/ledger/srev-062.md").read_text()

start = guimsg.index("_FX BOOLEAN Gui_Hook_DispatchMessage8(HMODULE module)")
end = guimsg.index("return TRUE;", start)
func = guimsg[start:end]

for term in [
    "SREV-295: opcode comments use parser terms from SREV-062.",
    "DispatchMessageA     mov edx,1           BA 01 00 00 00",
    "(10 bytes)      jmp rel32           E9 xx xx xx xx",
    "DispatchMessageW     xor edx,edx         33 D2",
    "(6 bytes)       jmp rel8            EB xx",
    "if (a[5] == 0xEB)",
    "else if (a[5] == 0xE9)",
    "else\n            return FALSE;",
    "if (w[2] == 0xEB)",
    "else if (w[2] == 0xE9)",
    "if ((a + a_offset) == (w + w_offset))",
]:
    require(func, term, "Gui_Hook_DispatchMessage8")

for stale in [
    "jmp xxx",
    "jmp short xxx",
]:
    reject(func, stale, "DispatchMessage opcode comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUIMSG_DISPATCH_STUB_OPCODE_COMMENT",
    "rel8",
    "rel32",
    "SREV-062",
    "Sandboxie-local compatibility schema",
    "no parser behavior change",
]:
    require(spec, term, "spec")

for term in [
    "GUI_DISPATCH_MESSAGE_STUB_PARSER",
    "EB rel8",
    "E9 rel32",
    "unknown opcodes must fail closed",
]:
    require(srev_062, term, "SREV-062 adjacency")

for term in [
    "### SREV-295: GuiMsg Dispatch Stub Opcode Comment",
    "GUIMSG_DISPATCH_STUB_OPCODE_COMMENT",
    "srev-295-guimsg-dispatch-stub-opcode-comment.schema.json",
    "Sandboxie/core/dll/guimsg.c",
    "Gui_Hook_DispatchMessage8",
    "SREV-062",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-295 source gate passed")
