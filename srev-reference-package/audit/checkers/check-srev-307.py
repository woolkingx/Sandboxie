#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-307 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-307 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-307-key-ie-protected-mode-fake-value-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-307 failed: schema is not draft-07")
if schema.get("id") != "KEY_IE_PROTECTED_MODE_FAKE_VALUE_OWNER":
    raise SystemExit("SREV-307 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-307 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_NtQueryValueKeyFakeForInternetExplorer owns IE Protected Mode REG_DWORD fake values for KeyValuePartialInformation",
    "ZwQueryValueKey owns the caller buffer, Length, ResultLength, and KeyValueInformationClass contract",
    "KEY_VALUE_PARTIAL_INFORMATION requires Type, DataLength, and counted Data bytes",
    "ProtectedModeOffForAllZones is a local exact-predicate compatibility value because public Microsoft documentation is sparse",
    "SREV-307 changes comments and proof only; no IE Protected Mode fake-value behavior changes",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-307-key-ie-protected-mode-fake-value-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-307.md").read_text()

start = key.index("_FX NTSTATUS Key_NtQueryValueKeyFakeForInternetExplorer(")
end = key.index("// Key_NtQueryValueKeyFakeForAcrobatReader", start)
func = key[start:end]

for term in [
    "Dll_ProcessFlags & SBIE_FLAG_RIGHTS_DROPPED",
    "SREV-307: IE zone Protected Mode policy. Microsoft documents",
    "Zones\\<n>\\2500 as the per-zone Protected Mode value; this fake",
    "route returns 3 only for that Zones path, exposing Protected",
    "Mode as off while preserving non-Zones value queries.",
    "ValueNameLen == 4 && _wcsicmp(ValueNameBuf, L\"2500\") == 0",
    "L\"\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\\"",
    "L\"Internet Settings\\\\Zones\"",
    "ValueData = 3;              // protected mode OFF",
    "SREV-307: IE may also probe this all-zones low-rights switch.",
    "Public Microsoft docs for this value are sparse, so the local",
    "contract is only the exact counted value-name match and DWORD 1.",
    "ValueNameLen == 27",
    "_wcsicmp(ValueNameBuf, L\"ProtectedModeOffForAllZones\") == 0",
    "ValueData = 1;                  // protected mode OFF",
    "SREV-307: suppress the IE Protected Mode warning banner alongside",
    "the off-mode fake values; Microsoft ESC script guidance documents",
    "this REG_DWORD preference under Internet Explorer\\Main.",
    "ValueNameLen == 21",
    "_wcsicmp(ValueNameBuf, L\"NoProtectedModeBanner\") == 0",
    "ValueData = 1;                  // don't show gold bar",
    "KEY_VALUE_PARTIAL_INFORMATION *kvpi",
    "kvpi->TitleIndex     = 0;",
    "kvpi->Type           = ValueType;",
    "kvpi->DataLength     = sizeof(ULONG);",
    "*(ULONG *)kvpi->Data = ValueData;",
    "*ResultLength = sizeof(ULONG) * 4;",
    "return STATUS_SUCCESS;",
    "return STATUS_BAD_INITIAL_PC;",
]:
    require(func, term, "Key_NtQueryValueKeyFakeForInternetExplorer")

for stale in [
    "hack:  if the Internet Explorer process is checking for",
    "hack:  if the Internet Explorer process is checking for value",
    "this alternate\n    // approach is sometimes used instead of the approach above",
    "warning that protected mode is turned off",
]:
    reject(func, stale, "source wording")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_IE_PROTECTED_MODE_FAKE_VALUE_OWNER",
    "comment-only source clarification, no behavior change",
    "No equivalent public Microsoft documentation was found",
    "No behavior changed: the `SBIE_FLAG_RIGHTS_DROPPED` skip",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-307: Key IE Protected Mode Fake Value Owner",
    "KEY_IE_PROTECTED_MODE_FAKE_VALUE_OWNER",
    "srev-307-key-ie-protected-mode-fake-value-owner.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_NtQueryValueKeyFakeForInternetExplorer",
    "ProtectedModeOffForAllZones",
    "NoProtectedModeBanner",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-307 source gate passed")
