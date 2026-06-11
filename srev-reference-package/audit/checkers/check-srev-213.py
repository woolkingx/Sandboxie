#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-213 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-213 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-213-reg-delete-v2-counted-value-name.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-213 failed: schema is not draft-07")
if schema.get("id") != "REG_DELETE_V2_COUNTED_VALUE_NAME":
    raise SystemExit("SREV-213 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key_del.c":
    raise SystemExit("SREV-213 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-213 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "delete-v2 marker path construction",
    "counted UNICODE_STRING buffers",
    "counted by NameLength",
    "synthesize a local terminator",
    "compatibility wrapper",
    "STATUS_INSUFFICIENT_RESOURCES",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-213-reg-delete-v2-counted-value-name.md").read_text()
key_del = (ROOT / "Sandboxie/core/dll/key_del.c").read_text()
key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
merge = (ROOT / "Sandboxie/core/dll/key_merge.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-213.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static NTSTATUS Key_MarkDeletedEx_v2(const WCHAR* TruePath, const WCHAR* ValueName, ULONG ValueNameLen);",
    "static ULONG Key_IsDeletedExLen_v2(const WCHAR* TruePath, const WCHAR* ValueName, ULONG ValueNameLen, BOOLEAN IsValue);",
    "static ULONG Key_IsDeletedEx_v2(const WCHAR* TruePath, const WCHAR* ValueName, BOOLEAN IsValue);",
]:
    require(key_del, term, "counted helper declaration")

mark = between(
    key_del,
    "_FX NTSTATUS Key_MarkDeletedEx_v2(const WCHAR* TruePath, const WCHAR* ValueName, ULONG ValueNameLen)",
    "//---------------------------------------------------------------------------\n// Key_IsDeleted_v2",
)
for term in [
    "ULONG TruePathLen = wcslen(TruePath);",
    "ULONG FullPathLen = TruePathLen + (ValueName ? ValueNameLen : 0) + 16;",
    "if (! FullPath) {\n        File_ReleaseMutex(hMutex);\n        return STATUS_INSUFFICIENT_RESOURCES;\n    }",
    "wmemcpy(FullPath, TruePath, TruePathLen);",
    "*ptr++ = L'\\\\';\n        *ptr++ = L'$';\n        wmemcpy(ptr, ValueName, ValueNameLen);",
    "*ptr = L'\\0';",
    "File_MarkDeleted_internal(&Key_PathRoot, FullPath, &bTruncated)",
]:
    require(mark, term, "counted delete marker construction")
reject(mark, "wcslen(ValueName)", "delete marker value-name wcslen")
reject(mark, "wcscat(FullPath, ValueName)", "delete marker value-name wcscat")

check_len = between(
    key_del,
    "_FX ULONG Key_IsDeletedExLen_v2(const WCHAR* TruePath, const WCHAR* ValueName, ULONG ValueNameLen, BOOLEAN IsValue)",
    "_FX ULONG Key_IsDeletedEx_v2",
)
for term in [
    "ULONG FullPathLen = TruePathLen + (ValueName ? ValueNameLen : 0) + 16;",
    "if (! FullPath)\n        return 0;",
    "wmemcpy(FullPath, TruePath, TruePathLen);",
    "if (IsValue)\n            *ptr++ = L'$';",
    "wmemcpy(ptr, ValueName, ValueNameLen);",
    "return Key_IsDeleted_v2(FullPath);",
]:
    require(check_len, term, "counted deleted check construction")
reject(check_len, "wcslen(ValueName)", "deleted check value-name wcslen")
reject(check_len, "wcscat(FullPath, ValueName)", "deleted check value-name wcscat")

wrapper = between(
    key_del,
    "_FX ULONG Key_IsDeletedEx_v2(const WCHAR* TruePath, const WCHAR* ValueName, BOOLEAN IsValue)",
    "//---------------------------------------------------------------------------\n// Key_HasDeleted_v2",
)
require(wrapper, "ValueName ? wcslen(ValueName) : 0", "null-terminated compatibility wrapper")

for term in [
    "Key_MarkDeletedEx_v2(TruePath, NULL, 0);",
    "Key_MarkDeletedEx_v2(TruePath, ValueName->Buffer, ValueName->Length / sizeof(WCHAR));",
    "Key_IsDeletedExLen_v2(TruePath, ValueNameBuf, ValueNameLen1, TRUE)",
    "ValueNameLen = ((KEY_VALUE_BASIC_INFORMATION *)KeyValueInformation)->NameLength / sizeof(WCHAR);",
    "ValueNameLen = ((KEY_VALUE_FULL_INFORMATION *)KeyValueInformation)->NameLength / sizeof(WCHAR);",
    "Key_IsDeletedExLen_v2(TruePath, ValueName, ValueNameLen, TRUE)",
]:
    require(key, term, "counted key.c call site")

reject(key, "Key_MarkDeletedEx_v2(TruePath, ValueName->Buffer);", "stale delete-value call")
reject(key, "Key_IsDeletedEx_v2(TruePath, ValueNameBuf, TRUE)", "stale query-value counted call")
reject(key, "Key_IsDeletedEx_v2(TruePath, ValueName, TRUE)", "stale enumerate-value counted call")

for term in [
    "Key_IsDeletedEx_v2(merge->name, subkey->name, FALSE)",
    "Key_IsDeletedEx_v2(merge->name, value->name, TRUE)",
]:
    require(merge, term, "generated merge-name wrapper preservation")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-213",
    "owner: Sandboxie/core/dll/key_del.c",
    "implementation: Sandboxie/core/dll/key.c",
    "spec: docs/plan/srev-213-reg-delete-v2-counted-value-name.md",
    "schema: docs/plan/srev-213-reg-delete-v2-counted-value-name.schema.json",
    "checker: docs/plan/check-srev-213.py",
    "patched source-level after official registry counted value-name shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-213 source gate passed")
