#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-308 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-308 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-308-key-createprocess-srp-authenticode-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-308 failed: schema is not draft-07")
if schema.get("id") != "KEY_CREATEPROCESS_SRP_AUTHENTICODE_OWNER":
    raise SystemExit("SREV-308 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/key.c":
    raise SystemExit("SREV-308 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_NtQueryValueKeyFakeForCreateProcess owns only the CreateProcess-time AuthenticodeEnabled REG_DWORD fake value",
    "ZwQueryValueKey owns the caller buffer, Length, ResultLength, and KeyValueInformationClass contract",
    "KEY_VALUE_PARTIAL_INFORMATION requires Type, DataLength, and counted Data bytes",
    "SRP certificate rules process Authenticode-signed EXE launch and may trigger CRL checks",
    "SREV-308 changes comments and proof only; no CreateProcess SRP fake-value behavior changes",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/dll/key.c").read_text()
advapi = (ROOT / "Sandboxie/core/dll/advapi.c").read_text()
token = (ROOT / "Sandboxie/core/drv/token.c").read_text()
spec = (ROOT / "docs/plan/srev-308-key-createprocess-srp-authenticode-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-308.md").read_text()

dispatch_start = key.index("_FX NTSTATUS Key_NtQueryValueKey(")
dispatch_end = key.index("// Key_NtQueryValueKeyFakeForInternetExplorer", dispatch_start)
dispatch = key[dispatch_start:dispatch_end]

start = key.index("_FX NTSTATUS Key_NtQueryValueKeyFakeForCreateProcess(")
end = key.index("// Key_NtEnumerateValueKey", start)
func = key[start:end]

for term in [
    "if (TlsData->proc_create_process) {",
    "status = Key_NtQueryValueKeyFakeForCreateProcess(",
    "if (status != STATUS_BAD_INITIAL_PC)",
]:
    require(dispatch, term, "Key_NtQueryValueKey dispatch")

for term in [
    "SREV-308: CreateProcess-time SRP certificate-rule policy.",
    "Microsoft documents SRP certificate rules as Authenticode/CRL",
    "processing for signed EXE launch. During Sandboxie process",
    "creation, keep this exact fake value disabled to avoid recursive",
    "SandboxieCrypto startup while SandboxieRpcSs is being loaded.",
    "if (Length < sizeof(ULONG) * 4)",
    "ValueNameLen == 19",
    "_wcsicmp(ValueNameBuf, L\"AuthenticodeEnabled\") == 0",
    "ValueData = 0;                  // AuthenticodeEnabled OFF",
    "KEY_VALUE_PARTIAL_INFORMATION *kvpi",
    "kvpi->TitleIndex     = 0;",
    "kvpi->Type           = ValueType;",
    "kvpi->DataLength     = sizeof(ULONG);",
    "*(ULONG *)kvpi->Data = ValueData;",
    "*ResultLength = sizeof(ULONG) * 4;",
    "return STATUS_SUCCESS;",
    "return STATUS_BAD_INITIAL_PC;",
]:
    require(func, term, "Key_NtQueryValueKeyFakeForCreateProcess")

for stale in [
    "the AuthenticodeEnabled registry value for SRP is queried during",
    "CreateProcess call to SandboxieCrypto, which will hang if",
    "loading SandboxieRpcSs, a dependency of SandboxieCrypto",
]:
    reject(func, stale, "source wording")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "KEY_CREATEPROCESS_SRP_AUTHENTICODE_OWNER",
    "comment-only source clarification, no behavior change",
    "No behavior changed: the `TlsData->proc_create_process` dispatcher",
    "AdvApi_EnableDisableSRP",
    "SANDBOX_INERT",
]:
    require(spec, term, "spec")

for term in [
    "CreateProcess uses SaferComputeTokenFromLevel to check SRP/AppLocker",
    "AdvApi_EnableDisableSRP",
    "AdvApi_EnableSRP = Enable;",
]:
    require(advapi, term, "advapi SRP adjacency")

for term in [
    "SRP/AppLocker use the process primary token for security",
    "SANDBOX_INERT",
    "Token_Restrict(OriginalToken, SANDBOX_INERT | DISABLE_MAX_PRIVILEGE, proc)",
]:
    require(token, term, "driver token SRP adjacency")

for term in [
    "### SREV-308: Key CreateProcess SRP Authenticode Owner",
    "KEY_CREATEPROCESS_SRP_AUTHENTICODE_OWNER",
    "srev-308-key-createprocess-srp-authenticode-owner.schema.json",
    "Sandboxie/core/dll/key.c",
    "Key_NtQueryValueKeyFakeForCreateProcess",
    "AuthenticodeEnabled",
    "SandboxieCrypto",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-308 source gate passed")
