#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-091 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-091 failed: schema is not draft-07")
if schema.get("id") != "HOOK_TRAMP_PUSH_RET_STUB_PRESERVATION":
    raise SystemExit("SREV-091 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "PUSH imm32 / RET envelope",
    "replace only the PUSH immediate operand",
    "must not rewrite that envelope into a relative E9 JMP",
    "existing E9 relative JMP path",
    "mov-rax / jmp-rax path",
    "instruction-cache coherency remain owned by caller hook-install paths such as SREV-058",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/hook_tramp.c").read_text()
spec = (ROOT / "docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.md").read_text()
ledger = read_combined_ledger(ROOT)
srev058 = (ROOT / "docs/plan/srev-058-dllhook-instruction-cache.md").read_text()

for term in [
    "if (SourceAddr[0] == 0x68 && SourceAddr[5] == 0xC3)",
    "PUSH routine_address        0x68 xx xx xx xx",
    "RET                         0xC3",
    "Preserve the same PUSH/RET instruction envelope and replace only",
    "owner shape the third-party unload code expects",
    "*(ULONG *)&SourceAddr[1] = (ULONG)JumpTarget;",
]:
    require(src, term, "hook_tramp.c PUSH/RET preservation path")

for stale in [
    "JMP, we get a crash when it unloads",
    "To prevent that, we",
]:
    if stale in src:
        raise SystemExit(f"SREV-091 failed: stale symptom-only comment remains {stale!r}")

push_index = src.index("if (SourceAddr[0] == 0x68 && SourceAddr[5] == 0xC3)")
operand_index = src.index("*(ULONG *)&SourceAddr[1] = (ULONG)JumpTarget;", push_index)
fallback_index = src.index("SourceAddr[0] = 0xE9;", operand_index)
if not (push_index < operand_index < fallback_index):
    raise SystemExit("SREV-091 failed: PUSH/RET operand rewrite must precede E9 fallback")

for term in [
    "SourceAddr[0] = 0xFA;",
    "SourceAddr[1] = 0x48;",
    "*(ULONG_PTR *)&SourceAddr[3] = (ULONG_PTR)JumpTarget;",
    "SourceAddr[11] = 0xFF;",
    "SourceAddr[12] = 0xE0;",
]:
    require(src, term, "hook_tramp.c 64-bit path preservation")

for term in [
    "DisableWriteProtect();",
    "EnableWriteProtect();",
    "WritableAddr",
    "ExecutableAddr",
]:
    require(src, term, "hook_tramp.c write boundary preservation")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "FlushInstructionCache",
    "Every user-mode executable-code mutation must be followed by",
]:
    require(srev058, term, "SREV-058 cache coherency owner")

for term in [
    "### SREV-091: Hook Trampoline PUSH/RET Stub Preservation",
    "HOOK_TRAMP_PUSH_RET_STUB_PRESERVATION",
    "srev-091-hook-tramp-push-ret-stub-preservation.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-091 schema/source gate passed")
