#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-173 failed: {label} missing {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-173-hook-tramp-code-capacity.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-173 failed: schema is not draft-07")
if schema.get("id") != "HOOK_TRAMP_CODE_CAPACITY":
    raise SystemExit("SREV-173 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "hook_inst.c owns source instruction analysis only and does not own destination trampoline capacity",
    "hook_tramp.c owns trampoline code emission and must bound check destination bytes against HOOK_TRAMP.code",
    "Hook_Tramp_EmitLength names the destination byte count for each local relocation shape before writes",
    "Hook_Tramp_HasCodeSpace proves current emission and reserved final jump back stub fit inside HOOK_TRAMP.code",
    "Hook_Tramp_Copy fails closed when expanded emission would overflow the trampoline code buffer",
    "SREV-173 does not change instruction decoding source byte counting relocation semantics allocation page protection or instruction cache ownership",
]:
    require(contracts, term, "schema")

hook_inst_c = (ROOT / "Sandboxie/core/dll/hook_inst.c").read_text()
hook_tramp_c = (ROOT / "Sandboxie/core/dll/hook_tramp.c").read_text()
hook_h = (ROOT / "Sandboxie/core/dll/hook.h").read_text()
drv_hook_c = (ROOT / "Sandboxie/core/drv/hook.c").read_text()
spec = (ROOT / "docs/plan/srev-173-hook-tramp-code-capacity.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-173.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "BOOLEAN Hook_Analyze(",
    "inst->len = (ULONG)(addr - (UCHAR *)address);",
    "inst->kind = INST_SYSCALL;",
    "inst->kind = INST_CTLXFER;",
]:
    require(hook_inst_c, term, "hook_inst.c analyzer surface")

for term in [
    "UCHAR code[64];",
    "ULONG count;",
    "BOOLEAN Hook_Analyze(",
]:
    require(hook_h, term, "hook.h trampoline/analyzer contract")

for term in [
    "ProbeForWrite(Trampoline, 96 /* sizeof(HOOK_TRAMP) */, 16);",
    "if (Hook_BuildTramp(Source, Trampoline, is64, TRUE))",
]:
    require(drv_hook_c, term, "driver trampoline API boundary")

for term in [
    "static BOOLEAN Hook_Tramp_HasCodeSpace(",
    "static ULONG Hook_Tramp_JumpBackSize(BOOLEAN is64);",
    "static ULONG Hook_Tramp_EmitLength(",
    "_FX BOOLEAN Hook_Tramp_HasCodeSpace(",
    "_FX ULONG Hook_Tramp_JumpBackSize(BOOLEAN is64)",
    "_FX ULONG Hook_Tramp_EmitLength(",
    "UCHAR *end = tramp->code + sizeof(tramp->code);",
    "if (code < begin || code > end)",
    "if (write_len > (ULONG)(end - code))",
    "if (reserve_len > (ULONG)(end - code))",
    "return is64 ? 10 : 6;",
    "return is64 ? 16 : 6;",
    "return is64 ? 14 : 5;",
    "return 16;",
    "return inst->len + 10 + (push_pop_rax ? 2 : 0);",
]:
    require(hook_tramp_c, term, "hook_tramp.c capacity helpers")

copy = section(hook_tramp_c, "_FX BOOLEAN Hook_Tramp_Copy(", "// Hook_BuildTramp")
for term in [
    "emit_len = Hook_Tramp_EmitLength(src, &inst, is64, push_pop_rax);",
    "if (! Hook_Tramp_HasCodeSpace(\n                tramp, code, emit_len, Hook_Tramp_JumpBackSize(is64)))\n            return FALSE;",
    "memcpy(code, src, inst.len);",
    "if (! Hook_Tramp_HasCodeSpace(\n            tramp, code, Hook_Tramp_JumpBackSize(is64), 0))\n        return FALSE;",
    "tramp->size = code_len;",
]:
    require(copy, term, "Hook_Tramp_Copy bounded emission")

for term in [
    "### SREV-173: Hook Trampoline Code Capacity",
    "HOOK_TRAMP_CODE_CAPACITY",
    "srev-173-hook-tramp-code-capacity.schema.json",
    "Sandboxie/core/dll/hook_inst.c",
    "Sandboxie/core/dll/hook_tramp.c",
    "HOOK_TRAMP.code",
    "Hook_Tramp_HasCodeSpace",
    "Hook_Tramp_EmitLength",
    "Windows x86",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-173 schema/source gate passed")
