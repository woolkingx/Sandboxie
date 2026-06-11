#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-304 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-304 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-304-key-trustedinstaller-storedirty-policy-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-304 failed: schema is not draft-07")
if schema.get("id") != "KEY_TRUSTEDINSTALLER_STOREDIRTY_POLICY_BOUNDARY":
    raise SystemExit("SREV-304 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-304 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_NtSetValueKey owns only the TrustedInstaller StoreDirty compatibility suppression branch",
    "ZwSetValueKey owns registry value create-or-replace behavior",
    "ValueName is a counted UNICODE_STRING value-name input",
    "SREV-213 owns adjacent counted registry value-name handling",
    "SREV-304 changes comments and proof only; no StoreDirty behavior changes",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-304-key-trustedinstaller-storedirty-policy-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-304.md").read_text()
srev_213 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-213.md").read_text(),
    (ROOT / "docs/plan/srev-213-reg-delete-v2-counted-value-name.md").read_text(),
    (ROOT / "docs/plan/srev-213-reg-delete-v2-counted-value-name.schema.json").read_text(),
])

start = key.index("_FX NTSTATUS Key_NtSetValueKey(")
end = key.index("// Key_NtQueryValueKey", start)
func = key[start:end]

for term in [
    "SREV-304: TrustedInstaller WinSxS assembly install compatibility.",
    "ZwSetValueKey would create or replace StoreDirty; this sandbox",
    "policy deliberately suppresses that one COMPONENTS marker so the",
    "installer can complete. Windows runtime proof owns any predicate",
    "change to the image, key path, value type, or data shape.",
    "if (Dll_ImageType == DLL_IMAGE_TRUSTED_INSTALLER &&",
    "uni.Length == 20 &&",
    "_wcsnicmp(uni.Buffer, L\"StoreDirty\", 10) == 0) {",
    "return STATUS_SUCCESS;",
    "status = __sys_NtSetValueKey(\n        KeyHandle, &uni, 0, Type, Data, DataSize);",
    "status = NtOpenKey(&handle, KEY_WRITE, &objattrs);",
]:
    require(func, term, "Key_NtSetValueKey")

for stale in [
    "A workaround is to just not create",
    "TrustedInstaller to complain",
    "exists, and aborts",
]:
    reject(func, stale, "source wording")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_TRUSTEDINSTALLER_STOREDIRTY_POLICY_BOUNDARY",
    "comment-only source clarification, no behavior change",
    "No behavior changed: the TrustedInstaller image check",
    "SREV-213 owns counted registry value-name handling",
]:
    require(spec, term, "spec")

for term in [
    "REG_DELETE_V2_COUNTED_VALUE_NAME",
    "Value names crossing from NtDeleteValueKey are counted UNICODE_STRING buffers",
    "KEY_VALUE_BASIC_INFORMATION.NameLength",
]:
    require(srev_213, term, "SREV-213 adjacency")

for term in [
    "### SREV-304: Key TrustedInstaller StoreDirty Policy Boundary",
    "KEY_TRUSTEDINSTALLER_STOREDIRTY_POLICY_BOUNDARY",
    "srev-304-key-trustedinstaller-storedirty-policy-boundary.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_NtSetValueKey",
    "SREV-213",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-304 source gate passed")
