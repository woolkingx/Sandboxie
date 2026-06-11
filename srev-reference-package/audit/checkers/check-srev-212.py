#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-212 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-212 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-212-process-hook-entry-disable-guard.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-212 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_HOOK_ENTRY_DISABLE_GUARD":
    raise SystemExit("SREV-212 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/process_hook.c":
    raise SystemExit("SREV-212 failed: wrong owner")
if schema.get("declaration") != "Sandboxie/core/drv/process.h":
    raise SystemExit("SREV-212 failed: wrong declaration")

contracts = "\n".join(schema["contracts"])
for term in [
    "generated hook-entry machine-code layout",
    "only creator for hook entries",
    "HOOK_TRAMP_CODE_TO_TRAMP_HEAD",
    "returns without patching",
    "changing test eax,eax to xor eax,eax",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-212-process-hook-entry-disable-guard.md").read_text()
src = (ROOT / "Sandboxie/core/drv/process_hook.c").read_text()
header = (ROOT / "Sandboxie/core/drv/process.h").read_text()
hook_header = (ROOT / "Sandboxie/core/dll/hook.h").read_text()
obj_xp = (ROOT / "Sandboxie/core/drv/obj_xp.c").read_text()
gui_xp = (ROOT / "Sandboxie/core/drv/gui_xp.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-212.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "ULONG_PTR Process_BuildHookEntry(",
    "void Process_DisableHookEntry(ULONG_PTR HookEntry);",
]:
    require(header, term, "process.h declaration boundary")

for term in [
    "typedef struct _HOOK_TRAMP",
    "ULONG eyecatcher;",
    "void *target;",
    "UCHAR code[64];",
    "#define HOOK_TRAMP_CODE_TO_TRAMP_HEAD(x)",
]:
    require(hook_header, term, "HOOK_TRAMP local schema")

build = between(
    src,
    "_FX ULONG_PTR Process_BuildHookEntry(",
    "//---------------------------------------------------------------------------\n// Process_DisableHookEntry",
)
for term in [
    "tramp = Hook_BuildTramp(NULL, NULL, FALSE, FALSE);",
    "tramp = HOOK_TRAMP_CODE_TO_TRAMP_HEAD(tramp);",
    "tramp->eyecatcher = tzuk;",
    "tramp->target = (void *)NewProc;",
    "pOldProc = (ULONG_PTR *)&tramp->code[sizeof(tramp->code) - 8];",
    "return (ULONG_PTR)&tramp->code;",
]:
    require(build, term, "hook entry creator schema")

disable = between(
    src,
    "_FX void Process_DisableHookEntry(ULONG_PTR HookEntry)",
    "\n}\n",
)
for term in [
    "HOOK_TRAMP *tramp = HOOK_TRAMP_CODE_TO_TRAMP_HEAD(HookEntry);",
    "UCHAR *code;",
    "if ((! HookEntry) || tramp->eyecatcher != tzuk)\n        return;",
    "code = &tramp->code[0];",
    "change 'test eax,eax' into 'xor eax,eax'",
    "*(test + PREFIX64) = 0x33;",
    "hotpatch[0] = 0xEB;",
    "*(USHORT *)code = *(USHORT *)&hotpatch[0];",
]:
    require(disable, term, "guarded disable schema")

if not disable.index("if ((! HookEntry)") < disable.index("code = &tramp->code[0];"):
    raise SystemExit("SREV-212 failed: code stream is derived before trampoline guard")
if not disable.index("code = &tramp->code[0];") < disable.index("*(test + PREFIX64) = 0x33;"):
    raise SystemExit("SREV-212 failed: code stream setup appears after byte patch")
if not disable.index("if ((! HookEntry)") < disable.index("*(test + PREFIX64) = 0x33;"):
    raise SystemExit("SREV-212 failed: eyecatcher guard appears after byte patch")

reject(disable, "UCHAR *code = &tramp->code[0];\n    UCHAR *test;", "unguarded code pointer setup")

for term in [
    "HookEntry = Process_BuildHookEntry(",
    "Process_DisableHookEntry(__jmp_##svc);",
]:
    require(obj_xp + gui_xp, term, "XP hook caller topology")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-212",
    "owner: Sandboxie/core/drv/process_hook.c",
    "declaration: Sandboxie/core/drv/process.h",
    "spec: docs/plan/srev-212-process-hook-entry-disable-guard.md",
    "schema: docs/plan/srev-212-process-hook-entry-disable-guard.schema.json",
    "checker: docs/plan/check-srev-212.py",
    "patched source-level after local trampoline schema and official process-notify shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-212 source gate passed")
