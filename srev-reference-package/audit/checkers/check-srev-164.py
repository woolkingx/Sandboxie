#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-164 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-164 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-164-x64-syscall-count-width.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-164 failed: schema is not draft-07")
if schema.get("id") != "X64_SYSCALL_COUNT_WIDTH":
    raise SystemExit("SREV-164 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "util_asm.asm owns the assembly implementation of Sbie_InvokeSyscall_asm",
    "the C-facing count parameter is ULONG count",
    "on x64 count arrives as the low 32 bits of RDX and the high 32 bits are not part of the ULONG contract",
    "the x64 trampoline must validate store compare and load the count through 32-bit register views edx r10d and ecx",
    "the count remains capped at 19 arguments before any stack copy",
    "Linux source gate is not Windows driver build or runtime proof",
]:
    require(contracts, term, "schema")

asm = (ROOT / "Sandboxie/core/drv/util_asm.asm").read_text()
syscall = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
syscall_win32 = (ROOT / "Sandboxie/core/drv/syscall_win32.c").read_text()
spec = (ROOT / "docs/plan/srev-164-x64-syscall-count-width.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-164.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NTSTATUS Sbie_InvokeSyscall_asm(void* func, ULONG count, void* args);",
    "status = Sbie_InvokeSyscall_asm(entry->ntos_func, entry->param_count, stack);",
]:
    require(syscall, term, "syscall.c caller")

for term in [
    "NTSTATUS Sbie_InvokeSyscall_asm(void* func, ULONG count, void* args);",
    "status = Sbie_InvokeSyscall_asm(entry->ntos_func",
]:
    require(syscall_win32, term, "syscall_win32.c caller")

x64 = section(asm, "Sbie_InvokeSyscall_asm PROC FRAME", "Sbie_InvokeSyscall_asm ENDP")
for term in [
    "cmp         edx, 13h ; if count > 19",
    "mov         r11, r8  ; args",
    "mov         r10d, edx ; count",
    "mov         rax, rcx ; func",
    "cmp         r10d, 4",
    "mov         ecx, r10d ; arg count",
    "sub         ecx, 4    ; skip the register passed args",
    "rep movsq",
    "mov         r9,  qword ptr [r11+18h]",
    "mov         r8,  qword ptr [r11+10h]",
    "mov         rdx, qword ptr [r11+08h]",
    "mov         rcx, qword ptr [r11+00h]",
    "call        rax",
]:
    require(x64, term, "x64 trampoline")

reject(x64, "cmp         rdx, 13h", "64-bit count cap")
reject(x64, "mov         r10, rdx ; count", "64-bit count store")
reject(x64, "cmp         r10, 4", "64-bit register-argument comparison")
reject(x64, "mov         rcx, r10 ; arg count", "64-bit rep count load")

x86 = section(asm, "_Sbie_InvokeSyscall_asm@12 PROC", "_Sbie_InvokeSyscall_asm@12 ENDP")
for term in [
    "cmp         dword ptr [ebp+10h+4h], 13h ; arg count @count",
    "mov         ecx, dword ptr [ebp+10h+4h] ; arg count @count",
    "rep movsd",
]:
    require(x86, term, "x86 trampoline unchanged")

for term in [
    "### SREV-164: x64 Syscall Count Width",
    "X64_SYSCALL_COUNT_WIDTH",
    "srev-164-x64-syscall-count-width.schema.json",
    "Sandboxie/core/drv/util_asm.asm",
    "Sbie_InvokeSyscall_asm",
    "ULONG count",
    "cmp         edx, 13h",
    "mov         r10d, edx",
    "mov         ecx, r10d",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-164 schema/source gate passed")
