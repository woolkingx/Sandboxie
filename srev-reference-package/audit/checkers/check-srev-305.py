#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-305 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-305 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-305-key-classes-enumeration-name-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-305 failed: schema is not draft-07")
if schema.get("id") != "KEY_CLASSES_ENUMERATION_NAME_OWNER":
    raise SystemExit("SREV-305 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-305 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_NtEnumerateKey owns caller-visible child-name presentation for merged registry enumeration",
    "HKU SID Software Classes enumeration must not expose current_classes for KeyBasicInformation or KeyNodeInformation",
    "KEY_BASIC_INFORMATION Name is a counted non-null-terminated child-name payload",
    "SREV-176 owns Key_GetName normalized registry path building",
    "SREV-305 changes comments and proof only; no enumeration behavior changes",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-305-key-classes-enumeration-name-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-305.md").read_text()
srev_176 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-176.md").read_text(),
    (ROOT / "docs/plan/srev-176-key-util-registry-path-shape.md").read_text(),
    (ROOT / "docs/plan/srev-176-key-util-registry-path-shape.schema.json").read_text(),
])

start = key.index("_FX NTSTATUS Key_NtEnumerateKey(")
end = key.index("// Key_NtEnumerateKeyFake", start)
func = key[start:end]

for term in [
    "SREV-305: HKU\\<sid>\\Software\\Classes is the caller-visible",
    "classes path, but Windows may resolve it through the user's",
    "merged classes root. KeyBasicInformation/KeyNodeInformation",
    "ask only for the child name, so this path stays on the",
    "fake-enumeration owner instead of returning current_classes.",
    "KeyInformationClass == KeyBasicInformation ||\n             KeyInformationClass == KeyNodeInformation",
    "SubkeyPathLen > _Registry_User_Len + 2",
    "SubkeyPath[_Registry_User_Len] == L'\\\\'",
    "SubkeyPath[_Registry_User_Len + 2] == L'-'",
    "_wcsnicmp(SubkeyPath, _Registry_User,",
    "_wcsicmp(backslash, L\"\\\\Software\\\\Classes\") == 0",
    "status = STATUS_ACCESS_DENIED;",
    "status = Key_NtEnumerateKeyFake(",
]:
    require(func, term, "Key_NtEnumerateKey")

for stale in [
    "returned name will be wrong",
    "(\"current_classes\" instead",
    "of \"classes\").  We fake a result for this case too",
]:
    reject(func, stale, "source wording")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_CLASSES_ENUMERATION_NAME_OWNER",
    "comment-only source clarification, no behavior change",
    "No behavior changed: the `KeyInformationClass` guard",
    "SREV-176 owns",
]:
    require(spec, term, "spec")

for term in [
    "KEY_UTIL_REGISTRY_PATH_SHAPE",
    "Key_GetName owns key path normalization",
    "Key_OpenIfBoxed must not create a second registry path builder from KEY_NAME_INFORMATION",
]:
    require(srev_176, term, "SREV-176 adjacency")

for term in [
    "### SREV-305: Key Classes Enumeration Name Owner",
    "KEY_CLASSES_ENUMERATION_NAME_OWNER",
    "srev-305-key-classes-enumeration-name-owner.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_NtEnumerateKey",
    "SREV-176",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-305 source gate passed")
