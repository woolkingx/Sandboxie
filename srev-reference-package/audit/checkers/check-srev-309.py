#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-309 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-309 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-309-key-save-merge-materialization-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-309 failed: schema is not draft-07")
if schema.get("id") != "KEY_SAVE_MERGE_MATERIALIZATION_BOUNDARY":
    raise SystemExit("SREV-309 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-309 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_NtSaveKey and Key_NtSaveKeyEx currently delegate to native save of the physical key tree behind KeyHandle",
    "RegSaveKey and RegSaveKeyEx save a specified key plus subkeys and values to a registry file",
    "Sandboxie Key_Merge owns virtual host+box registry enumeration and query semantics",
    "Pre-save materialization is a separate registry-copy topology and requires Windows hive-save runtime proof before source behavior changes",
    "SREV-309 changes comments and proof only; no NtSaveKey or NtSaveKeyEx behavior changes",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-309-key-save-merge-materialization-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-309.md").read_text()

save_start = key.index("_FX NTSTATUS Key_NtSaveKey(")
save_end = key.index("// Key_NtSaveKeyEx", save_start)
save = key[save_start:save_end]

save_ex_start = key.index("_FX NTSTATUS Key_NtSaveKeyEx(")
save_ex_end = key.index("// Key_NtLoadKeyImpl", save_ex_start)
save_ex = key[save_ex_start:save_ex_end]

for term in [
    "SREV-309: NtSaveKey saves the physical key tree reached by KeyHandle.",
    "Sandboxie's merged host+box view is not materialized here; pre-save",
    "materialization needs a Windows hive-save runtime gate before change.",
    "SbieApi_Log(2205, L\"NtSaveKey\");",
    "return __sys_NtSaveKey(KeyHandle, FileHandle);",
]:
    require(save, term, "Key_NtSaveKey")

for term in [
    "SREV-309: NtSaveKeyEx has the same physical-tree boundary as NtSaveKey.",
    "Flags do not make the sandbox merge view durable; pre-save",
    "materialization needs a Windows hive-save runtime gate before change.",
    "SbieApi_Log(2205, L\"NtSaveKeyEx\");",
    "return __sys_NtSaveKeyEx(KeyHandle, FileHandle, Flags);",
]:
    require(save_ex, term, "Key_NtSaveKeyEx")

for stale in [
    "todo: copy all reg keys from host to box for the used KeyHandle",
]:
    reject(save + save_ex, stale, "source TODO")

for term in [
    "Key_Merge(",
    "Key_NtEnumerateKey(",
    "Key_NtEnumerateValueKey(",
    "Key_NtQueryValueKey(",
]:
    require(key, term, "key merge/enumeration adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_SAVE_MERGE_MATERIALIZATION_BOUNDARY",
    "No behavior changed: `SbieApi_Log(2205, ...)`, `__sys_NtSaveKey`, and",
    "classification and proof entry",
    "Runtime gate: Windows hive-save smoke",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-309: Key Save Merge Materialization Boundary",
    "KEY_SAVE_MERGE_MATERIALIZATION_BOUNDARY",
    "srev-309-key-save-merge-materialization-boundary.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_NtSaveKey",
    "Key_NtSaveKeyEx",
    "Key_Merge",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-309 source gate passed")
