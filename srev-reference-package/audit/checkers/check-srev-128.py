#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-128 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-128 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-128-gui-xp-hook-trampoline-failure-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-128 failed: schema is not draft-07")
if schema.get("id") != "GUI_XP_HOOK_TRAMPOLINE_FAILURE_LIFETIME":
    raise SystemExit("SREV-128 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gui_HookService stores the original source function pointer in owner-local storage before any failure edge can free the hook context",
    "GUI_HOOKSERVICE_CONTEXT SaveBytesAddr mirrors the original source function pointer but is not the failure-restore owner after context cleanup",
    "Hook_BuildTramp may return NULL when instruction analysis or trampoline allocation/copy fails",
    "Gui_HookService checks the Hook_BuildTramp result before SpySweeper push-jump trampoline writes through it",
    "push_jmp_target special trampoline patching only runs after Trampoline is non-null",
    "failure cleanup never dereferences context after ExFreePoolWithTag(context, tzuk)",
    "XP win32k service discovery hotfix prolog handling MDL locking and DPC freeze topology are unchanged",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/gui_xp.c").read_text()
tramp_source = (ROOT / "Sandboxie/core/dll/hook_tramp.c").read_text()
spec = (ROOT / "docs/plan/srev-128-gui-xp-hook-trampoline-failure-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "_FX void *Hook_BuildTramp(",
    "if (! Hook_Tramp_CountBytes(SourceFunc, &ByteCount, is64, probe))\n            return NULL;",
    "if (! tramp)\n        return NULL;",
    "if (! Hook_Tramp_Copy(tramp, SourceFunc, ByteCount, is64, probe))\n            return NULL;",
    "return &tramp->code;",
]:
    require(tramp_source, term, "Hook_BuildTramp local NULL shape")

hook = source[
    source.index("_FX BOOLEAN Gui_HookService("):
    source.index("// Gui_HookSaveThreads")
]

for term in [
    "void *OriginalSourceFunc;",
    "Trampoline = NULL;\n    OriginalSourceFunc = *pSourceFunc;",
    "context->SaveBytesAddr = OriginalSourceFunc;",
    "Trampoline = Hook_BuildTramp(",
    "if (! Trampoline) {\n        status = STATUS_UNSUCCESSFUL;\n        goto finish;\n    }\n\n    //\n    // if we detected SpySweeper hooks",
    "if (push_jmp_target) {",
    "*pSourceFunc = Trampoline;",
    "*pJumpStub = Process_BuildHookEntry(",
    "Hook_BuildJump(\n                    WriteAddr, context->SourceAddr, context->TargetAddr);",
    "ExFreePoolWithTag(context, tzuk);",
    "*pJumpStub = 0;\n        *pSourceFunc = OriginalSourceFunc;",
]:
    require(hook, term, "Gui_HookService")

if hook.index("if (! Trampoline)") > hook.index("if (push_jmp_target) {"):
    raise SystemExit("SREV-128 failed: trampoline null gate is after push_jmp_target write")

finish = hook[hook.index("finish:"):]
if finish.index("ExFreePoolWithTag(context, tzuk);") > finish.index("if (! NT_SUCCESS(status))"):
    raise SystemExit("SREV-128 failed: context free moved after failure restore")
failure_tail = finish[finish.index("if (! NT_SUCCESS(status))"):]
reject(failure_tail, "context->SaveBytesAddr", "post-free context restore")
reject(hook, "*pSourceFunc = context->SaveBytesAddr;", "old context-owned restore")

for term in [
    "### SREV-128: GUI XP Hook Trampoline Failure Lifetime",
    "GUI_XP_HOOK_TRAMPOLINE_FAILURE_LIFETIME",
    "srev-128-gui-xp-hook-trampoline-failure-lifetime.schema.json",
    "Sandboxie/core/drv/gui_xp.c",
    "Sandboxie/core/dll/hook_tramp.c",
    "Gui_HookService",
    "Hook_BuildTramp",
    "push_jmp_target",
    "OriginalSourceFunc",
    "ExFreePoolWithTag",
    "Process_BuildHookEntry",
]:
    require(ledger, term, "ledger")

print("SREV-128 schema/source gate passed")
