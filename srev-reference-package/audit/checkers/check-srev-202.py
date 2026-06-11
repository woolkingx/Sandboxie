#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-202 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-202 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-202-xp-object-type-hook-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-202 failed: schema is not draft-07")
if schema.get("id") != "XP_OBJECT_TYPE_HOOK_CONTRACT":
    raise SystemExit("SREV-202 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/obj_xp.c":
    raise SystemExit("SREV-202 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "validates TypeName, NewProc, OldProc, and pHookEntry",
    "bounds the ObjectName buffer including prefix and null terminator",
    "rejects ProcOffset values that cannot address a ULONG_PTR inside object->TypeInfo",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/drv/obj_xp.c").read_text()
spec = (ROOT / "docs/plan/srev-202-xp-object-type-hook-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-202.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static BOOLEAN Obj_BuildObjectTypeName(",
    "if ((! TypeName) || (! NewProc) || (! OldProc) || (! pHookEntry))",
    "STATUS_INVALID_PARAMETER",
    "Obj_BuildObjectTypeName(\n            ObjectName, sizeof(ObjectName) / sizeof(WCHAR), TypeName)",
]:
    require(src, term, "Obj_HookAnyProc input/path gate")

reject(src, "wcscpy(ObjectName, L\"\\\\ObjectTypes\\\\\");", "unchecked object name copy")
reject(src, "wcscat(ObjectName, TypeName);", "unchecked object name concat")

builder = between(
    src,
    "_FX BOOLEAN Obj_BuildObjectTypeName(",
    "return TRUE;",
)
for term in [
    "Prefix = L\"\\\\ObjectTypes\\\\\";",
    "PrefixLen = (ULONG)wcslen(Prefix);",
    "TypeLen = (ULONG)wcslen(TypeName);",
    "if (PrefixLen >= ObjectNameChars)",
    "if (TypeLen >= ObjectNameChars - PrefixLen)",
    "memcpy(ObjectName, Prefix, PrefixLen * sizeof(WCHAR));",
    "memcpy(ObjectName + PrefixLen, TypeName, (TypeLen + 1) * sizeof(WCHAR));",
]:
    require(builder, term, "bounded object type name builder")

hook = between(
    src,
    "_FX BOOLEAN Obj_HookAnyProc(",
    "_FX BOOLEAN Obj_BuildObjectTypeName(",
)
for term in [
    "if (ProcOffset > sizeof(object->TypeInfo) - sizeof(ULONG_PTR))",
    "status = STATUS_INVALID_PARAMETER;",
    "ProcPtr = (ULONG_PTR)(((UCHAR *)&object->TypeInfo) + ProcOffset);",
    "*OldProc = *(ULONG_PTR *)ProcPtr;",
    "HookEntry = Process_BuildHookEntry(",
    "if (! HookEntry)",
    "*pHookEntry = HookEntry;",
    "KeMemoryBarrier();",
    "InterlockedExchangePointer(",
]:
    require(hook, term, "hook publish topology")

if not hook.index("if (ProcOffset > sizeof(object->TypeInfo) - sizeof(ULONG_PTR))") < hook.index("ProcPtr ="):
    raise SystemExit("SREV-202 failed: ProcOffset gate is after ProcPtr calculation")
if not hook.index("if (ProcOffset > sizeof(object->TypeInfo) - sizeof(ULONG_PTR))") < hook.index("*OldProc ="):
    raise SystemExit("SREV-202 failed: ProcOffset gate is after OldProc read")
if not hook.index("if (! HookEntry)") < hook.index("InterlockedExchangePointer("):
    raise SystemExit("SREV-202 failed: hook publish is not gated by Process_BuildHookEntry")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-202",
    "owner: Sandboxie/core/drv/obj_xp.c",
    "spec: docs/plan/srev-202-xp-object-type-hook-contract.md",
    "schema: docs/plan/srev-202-xp-object-type-hook-contract.schema.json",
    "checker: docs/plan/check-srev-202.py",
    "patched source-level after official object-manager shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-202 source gate passed")
