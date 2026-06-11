#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-094 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-094-ldr-inject-stack-zero-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-094 failed: schema is not draft-07")
if schema.get("id") != "LDR_INJECT_STACK_ZERO_OWNER":
    raise SystemExit("SREV-094 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ldr_Inject_Entry restores original entrypoint bytes",
    "0x200-byte former injection frame",
    "first allocate that 0x200-byte range by moving ESP/RSP",
    "restore ESP/RSP before returning or jumping",
    "x86 stub keeps the stdcall-style return",
    "x64 stub keeps the existing jump-to-returned-entrypoint path",
    "does not change the patched entrypoint bytes",
]:
    require(contracts, term, "schema")

util32 = (ROOT / "Sandboxie/core/dll/util_32.asm").read_text()
util64 = (ROOT / "Sandboxie/core/dll/util_64.asm").read_text()
ldr_init = (ROOT / "Sandboxie/core/dll/ldr_init.c").read_text()
spec = (ROOT / "docs/plan/srev-094-ldr-inject-stack-zero-owner.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Ldr_Inject_Entry32@0        PROC C PUBLIC",
    "push esp            ; pRetAddr parameter",
    "call _Ldr_Inject_Entry@4",
    "F-Secure compatibility: clear the former injection frame only while",
    "sub esp,200h",
    "mov edi,esp",
    "rep stosd",
    "add esp,200h",
    "ret",
]:
    require(util32, term, "util_32.asm owner stack zero")

for term in [
    "Ldr_Inject_Entry64      PROC",
    "call Ldr_Inject_Entry",
    "mov rdx, rax",
    "F-Secure compatibility: clear the former injection frame only while",
    "sub rsp,200h",
    "mov rdi,rsp",
    "rep stosq",
    "add rsp,200h",
    "jmp rdx",
]:
    require(util64, term, "util_64.asm owner stack zero")

for stale in [
    "; $Workaround$ - 3rd party fix",
    "lea edi,[esp-200h]",
    "lea rdi,[rsp-200h]",
]:
    if stale in util32 or stale in util64:
        raise SystemExit(f"SREV-094 failed: stale below-stack/workaround shape remains {stale!r}")

util32_stub = util32[
    util32.index("Ldr_Inject_Entry32@0        PROC C PUBLIC"):
    util32.index("Ldr_Inject_Entry32@0        ENDP")
]
util64_stub = util64[
    util64.index("Ldr_Inject_Entry64      PROC"):
    util64.index("Ldr_Inject_Entry64      ENDP")
]

for text, reg, exit_op in [(util32_stub, "esp", "ret"), (util64_stub, "rsp", "jmp rdx")]:
    sub = text.find(f"sub {reg},200h")
    mov = text.find(f"mov {'edi' if reg == 'esp' else 'rdi'},{reg}")
    rep = text.find("rep stos")
    add = text.find(f"add {reg},200h")
    out = text.find(exit_op)
    if not (sub != -1 and sub < mov < rep < add < out):
        raise SystemExit(f"SREV-094 failed: {reg} owner/restore order is wrong")

for term in [
    "*entrypoint = 0xE8;",
    "(UCHAR *)Ldr_Inject_Entry32 - (entrypoint + 5)",
    "entrypoint[10] = 0xFF;",
    "entrypoint[11] = 0xE0;",
    "_FX void* Ldr_Inject_Entry(ULONG_PTR *pPtr)",
    "return entrypoint;",
]:
    require(ldr_init, term, "ldr_init.c injection topology")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "beyond current `RSP` as volatile",
    "remove the zeroing and does not broaden it",
    "same 0x200-byte",
    "Source gates prove",
]:
    require(spec, term, "spec owner classification")

for term in [
    "### SREV-094: Ldr Inject Stack-Zero Owner",
    "LDR_INJECT_STACK_ZERO_OWNER",
    "srev-094-ldr-inject-stack-zero-owner.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-094 schema/source gate passed")
