#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-133 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-133 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-133-low-x64-entry-nonvolatile-register.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-133 failed: schema is not draft-07")
if schema.get("id") != "LOW_X64_ENTRY_NONVOLATILE_REGISTER":
    raise SystemExit("SREV-133 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "_Start is a detour prelude and must not clobber x64 nonvolatile registers before jumping to the LdrInitializeThunk trampoline",
    "Windows x64 treats RBX RBP RDI RSI RSP R12 R13 R14 and R15 as nonvolatile registers",
    "Windows x64 treats RAX RCX RDX R8 R9 R10 and R11 as volatile registers",
    "_Start may use volatile scratch registers while preparing EntrypointC arguments",
    "_Start must not use RBX as an unbalanced scratch register",
    "SystemService x64 keeps its own RBX and RDI save/restore contract unchanged",
]:
    require(contracts, term, "schema")

entry = (ROOT / "Sandboxie/core/low/entry_asm.asm").read_text()
spec = (ROOT / "docs/plan/srev-133-low-x64-entry-nonvolatile-register.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

x64_start = entry[
    entry.index("ifdef _WIN64\t; 64-bit"):
    entry.index("else \t\t; 32-bit")
]
for term in [
    "EXTERN \t\tEntrypointC : PROC",
    "_Start:",
    "sub\trsp, 28h",
    "mov\tqword ptr [rsp+4*8], rcx",
    "mov\tqword ptr [rsp+5*8], rdx",
    "mov\tqword ptr [rsp+6*8], r8",
    "mov\tqword ptr [rsp+7*8], r9",
    "call\t$+5",
    "_001:\tpop     rcx",
    "mov r10,rcx",
    "add\trcx, offset SbieLowData - _001",
    "mov rdx,r10",
    "add rdx, offset _DetourCode - _001",
    "mov r8,r10",
    "add r8, offset _SystemService - _001",
    "call\tEntrypointC",
    "mov\trcx, qword ptr [rsp+4*8]",
    "mov\trdx, qword ptr [rsp+5*8]",
    "mov\tr8, qword ptr [rsp+6*8]",
    "mov\tr9, qword ptr [rsp+7*8]",
    "add\trsp, 28h",
    "jmp\trax",
]:
    require(x64_start, term, "x64 _Start")

for stale in [
    "mov rbx,rcx",
    "mov rdx,rbx",
    "mov r8,rbx",
]:
    reject(x64_start, stale, "stale RBX scratch in x64 _Start")

if x64_start.index("call\tEntrypointC") > x64_start.index("mov\trcx, qword ptr [rsp+4*8]"):
    raise SystemExit("SREV-133 failed: argument restore moved before EntrypointC")
if x64_start.index("mov\tr9, qword ptr [rsp+7*8]") > x64_start.index("jmp\trax"):
    raise SystemExit("SREV-133 failed: trampoline jump occurs before original argument restore")

x86_start = entry[
    entry.index("else \t\t; 32-bit"):
    entry.index(";----------------------------------------------------------------------------\n; SystemService")
]
for term in [
    "EXTERN \t\t_EntrypointC@12 : PROC",
    "add eax, offset _SystemService - _001",
    "add eax, offset _DetourCode - _001",
    "add\teax, offset SbieLowData - _001",
    "call\t_EntrypointC@12",
    "jmp\teax",
]:
    require(x86_start, term, "x86 _Start")

x64_service = entry[
    entry.index("ifdef _WIN64\t; 64-bit\nmyService Proc"):
    entry.index("myService ENDP")
]
for term in [
    "push rdi; target rsp",
    "push rbx; target rip",
    "pop rbx",
    "pop rdi",
    "ret",
]:
    require(x64_service, term, "x64 SystemService save/restore")

for term in [
    "### SREV-133: Low x64 Entry Nonvolatile Register",
    "LOW_X64_ENTRY_NONVOLATILE_REGISTER",
    "srev-133-low-x64-entry-nonvolatile-register.schema.json",
    "Sandboxie/core/low/entry_asm.asm",
    "Sandboxie/core/low/init.c",
    "_Start",
    "EntrypointC",
    "LdrInitializeThunk",
    "rbx",
    "r10",
    "SystemService",
]:
    require(ledger, term, "ledger")

print("SREV-133 schema/source gate passed")
