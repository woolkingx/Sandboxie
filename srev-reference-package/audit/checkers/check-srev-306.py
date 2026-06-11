#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-306 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-306 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-306-key-acrobat-fake-value-policy-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-306 failed: schema is not draft-07")
if schema.get("id") != "KEY_ACROBAT_FAKE_VALUE_POLICY_OWNER":
    raise SystemExit("SREV-306 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-306 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_NtQueryValueKeyFakeForAcrobatReader owns only Adobe preference REG_DWORD fake values for KeyValuePartialInformation",
    "ZwQueryValueKey owns the caller buffer, Length, ResultLength, and KeyValueInformationClass contract",
    "KEY_VALUE_PARTIAL_INFORMATION requires Type, DataLength, and counted Data bytes",
    "Non-matching Adobe fake-value queries must return STATUS_BAD_INITIAL_PC and fall through to normal registry handling",
    "SREV-306 changes comments and proof only; no Acrobat fake-value behavior changes",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-306-key-acrobat-fake-value-policy-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-306.md").read_text()

start = key.index("_FX NTSTATUS Key_NtQueryValueKey(")
end = key.index("// Key_NtQueryValueKeyFakeForInternetExplorer", start)
dispatch = key[start:end]

fake_start = key.index("_FX NTSTATUS Key_NtQueryValueKeyFakeForAcrobatReader(")
fake_end = key.index("// Key_NtQueryValueKeyFakeForCreateProcess", fake_start)
fake_with_comment = key[key.rfind("// SREV-306:", 0, fake_start):fake_end]

for term in [
    "KeyValueInformationClass == KeyValuePartialInformation",
    "KeyValueInformation && ResultLength",
    "SREV-306: Acrobat/AcroPDF-compatible callers share this",
    "KeyValuePartialInformation fake-value policy for Adobe REG_DWORD",
    "preferences. The fake owner must return a complete partial value",
    "buffer or STATUS_BAD_INITIAL_PC for normal registry handling.",
    "Dll_ImageType == DLL_IMAGE_ACROBAT_READER",
    "Dll_ImageType == DLL_IMAGE_PLUGIN_CONTAINER",
    "Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME",
    "Dll_ImageType == DLL_IMAGE_INTERNET_EXPLORER",
    "status = Key_NtQueryValueKeyFakeForAcrobatReader(",
]:
    require(dispatch, term, "Key_NtQueryValueKey dispatch")

for term in [
    "SREV-306: Adobe preference fake-value owner. This routine only fabricates",
    "REG_DWORD KeyValuePartialInformation for bProtectedMode and iCheckReader;",
    "non-matches fall through to the normal registry merge/query path.",
    "if (Length < sizeof(ULONG) * 4)",
    "ValueNameLen == 14",
    "_wcsicmp(ValueNameBuf, L\"bProtectedMode\") == 0",
    "ValueData = 0;                  // protected mode OFF",
    "ValueNameLen == 12",
    "_wcsicmp(ValueNameBuf, L\"iCheckReader\") == 0",
    "ValueData = 0;                  // update check OFF",
    "KEY_VALUE_PARTIAL_INFORMATION *kvpi",
    "kvpi->TitleIndex     = 0;",
    "kvpi->Type           = ValueType;",
    "kvpi->DataLength     = sizeof(ULONG);",
    "*(ULONG *)kvpi->Data = ValueData;",
    "*ResultLength = sizeof(ULONG) * 4;",
    "return STATUS_SUCCESS;",
    "return STATUS_BAD_INITIAL_PC;",
]:
    require(fake_with_comment, term, "Key_NtQueryValueKeyFakeForAcrobatReader")

for stale in [
    "$Workaround$ - 3rd party fix\n        if (Dll_ImageType == DLL_IMAGE_ACROBAT_READER",
    "$Workaround$ - 3rd party fix\n_FX NTSTATUS Key_NtQueryValueKeyFakeForAcrobatReader",
]:
    reject(key, stale, "source wording")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_ACROBAT_FAKE_VALUE_POLICY_OWNER",
    "comment-only source clarification, no behavior change",
    "No behavior changed: the image predicates",
    "STATUS_BAD_INITIAL_PC means fall through to normal merge/query handling",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-306: Key Acrobat Fake Value Policy Owner",
    "KEY_ACROBAT_FAKE_VALUE_POLICY_OWNER",
    "srev-306-key-acrobat-fake-value-policy-owner.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_NtQueryValueKeyFakeForAcrobatReader",
    "bProtectedMode",
    "iCheckReader",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-306 source gate passed")
