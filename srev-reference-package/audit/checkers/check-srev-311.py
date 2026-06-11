#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-311 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-311 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-311-key-rule-dummy-lastwrite-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-311 failed: schema is not draft-07")
if schema.get("id") != "KEY_RULE_DUMMY_LASTWRITE_OWNER":
    raise SystemExit("SREV-311 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key_merge.c":
    raise SystemExit("SREV-311 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_MergeCacheDummys owns metadata for rule-derived dummy subkeys",
    "ZwQueryKey with KeyBasicInformation can return LastWriteTime for an open key handle",
    "KEY_NODE_INFORMATION LastWriteTime is caller-visible registry subkey metadata",
    "Query failure must preserve dummy subkey visibility with the existing zero fallback",
    "SREV-311 changes only dummy subkey LastWriteTime metadata, not rule inclusion or merge ordering",
]:
    require(contracts, term, "schema")

merge_src = (ROOT / "Sandboxie/core/dll/key_merge.c").read_text()
key_src = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-311-key-rule-dummy-lastwrite-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-311.md").read_text()

start = merge_src.index("_FX NTSTATUS Key_MergeCacheDummys(")
end = merge_src.index("// Key_MergeCacheSubkeys", start)
func = merge_src[start:end]

for term in [
    "KEY_BASIC_INFORMATION info;",
    "ULONG info_len;",
    "SbieDll_GetReadablePaths(L'k', lists);",
    "status = SbieApi_OpenKey(&KeyHandle, FakePath);",
    "status = __sys_NtQueryKey(\n                        KeyHandle, KeyBasicInformation,\n                        &info, sizeof(KEY_BASIC_INFORMATION), &info_len);",
    "File_NtCloseImpl(KeyHandle);",
    "if (NT_SUCCESS(status) || status == STATUS_BUFFER_OVERFLOW)\n                        subkey->LastWriteTime = info.LastWriteTime;",
    "else\n                        subkey->LastWriteTime.QuadPart = 0;",
    "subkey->TitleOrClass = FALSE;",
    "if (cmp == 0) goto next;",
]:
    require(func, term, "Key_MergeCacheDummys")

query = func.index("status = __sys_NtQueryKey(")
close = func.index("File_NtCloseImpl(KeyHandle);", query)
copy = func.index("subkey->LastWriteTime = info.LastWriteTime;", close)
fallback = func.index("subkey->LastWriteTime.QuadPart = 0;", copy)
if not query < close < copy < fallback:
    raise SystemExit("SREV-311 failed: query/close/copy/fallback ordering is wrong")

reject(func, "subkey->LastWriteTime.QuadPart = 0; // todo: fix-me", "source TODO")

for term in [
    "Key_NtEnumerateKeyFake(",
    "*(LARGE_INTEGER *)KeyInformation = *LastWriteTime;",
    "KeyInformationClass == KeyNodeInformation",
]:
    require(key_src, term, "fake enumeration sink")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_RULE_DUMMY_LASTWRITE_OWNER",
    "SbieApi_OpenKey(FakePath)",
    "No readable-path scan, path-component extraction, duplicate suppression",
    "Runtime gate: Windows rule-specificity registry enumeration smoke",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-311: Key Rule Dummy LastWrite Owner",
    "KEY_RULE_DUMMY_LASTWRITE_OWNER",
    "srev-311-key-rule-dummy-lastwrite-owner.schema.json",
    "Sandboxie/core/dll/key_merge.c",
    "Key_MergeCacheDummys",
    "LastWriteTime",
    "Key_NtEnumerateKeyFake",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-311 source gate passed")
