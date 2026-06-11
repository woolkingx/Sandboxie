#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-325 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-325 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-325 failed: schema is not draft-07")
if schema.get("id") != "SECURE_ELEVATION_FLAGS_FAKE_ADMIN_ALLOWLIST":
    raise SystemExit("SREV-325 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/secure.c":
    raise SystemExit("SREV-325 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "official UAC and token documentation owns elevation semantics",
    "RtlQueryElevationFlags is a local observed ntdll hook target",
    "Secure_Init owns only the process and image allowlist",
    "Secure_RtlQueryElevationFlags owns the local decision",
    "IE Protected Mode registry fake values remain owned by SREV-307",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

secure = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
spec = (ROOT / "docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.md").read_text()
srev_307 = (
    (ROOT / "docs/plan/ledger/srev-307.md").read_text()
    + "\n"
    + (ROOT / "docs/plan/srev-307-key-ie-protected-mode-fake-value-owner.md").read_text()
)
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-325.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

init_start = secure.index("_FX BOOLEAN Secure_Init(void)")
init_end = secure.index("return TRUE;", init_start)
init_block = secure[init_start:init_end]

for term in [
    "RtlQueryElevationFlags =",
    "GetProcAddress(Dll_Ntdll, \"RtlQueryElevationFlags\");",
    "SBIEDLL_HOOK(Secure_,RtlQueryElevationFlags);",
    "SREV-325: allowlist for RtlQueryElevationFlags zero-flag faking.",
    "IE, SbieSvc/RpcSs brokers, and Synaptics callers are handled below.",
    "Secure_ShouldFakeRunningAsAdmin =",
    "Dll_ImageType == DLL_IMAGE_SANDBOXIE_SBIESVC",
    "Dll_ImageType == DLL_IMAGE_SANDBOXIE_RPCSS",
    "Dll_ImageType == DLL_IMAGE_INTERNET_EXPLORER",
    "_wcsicmp(Dll_ImageName, L\"SynTPEnh.exe\") == 0",
    "_wcsicmp(Dll_ImageName, L\"SynTPHelper.exe\") == 0",
    "Secure_IsInternetExplorerTabProcess",
    "SH_GetInternetExplorerVersion() >= 10",
    "Dll_ProcessFlags & SBIE_FLAG_RIGHTS_DROPPED",
    "Secure_Is_IE_NtQueryInformationToken = TRUE;",
]:
    require(init_block, term, "Secure_Init allowlist")

reject(init_block, "$Workaround$ - 3rd party fix", "Secure_Init allowlist comment")

func_start = secure.index("_FX NTSTATUS Secure_RtlQueryElevationFlags(ULONG *Flags)")
func_end = secure.index("//---------------------------------------------------------------------------", func_start + 1)
func = secure[func_start:func_end]

for term in [
    "if (Secure_FakeAdmin || TlsData->proc_create_process_fake_admin)",
    "else if (Secure_ShouldFakeRunningAsAdmin)",
    "if (Dll_ImageType == DLL_IMAGE_INTERNET_EXPLORER)",
    "if (! TlsData->proc_create_process)\n                fake = TRUE;",
    "else if (Dll_ImageType == DLL_IMAGE_SANDBOXIE_SBIESVC)",
    "if (TlsData->proc_create_process)\n                fake = TRUE;",
    "fake = TRUE;",
    "*Flags = 0;",
    "status = STATUS_SUCCESS;",
    "status = __sys_RtlQueryElevationFlags(Flags);",
]:
    require(func, term, "Secure_RtlQueryElevationFlags")

fake_assign = func.index("*Flags = 0;")
native = func.index("status = __sys_RtlQueryElevationFlags(Flags);")
if not fake_assign < native:
    raise SystemExit("SREV-325 failed: fake zero flags must stay before native fallback")

for term in [
    "KEY_IE_PROTECTED_MODE_FAKE_VALUE_OWNER",
    "Key_NtQueryValueKeyFakeForInternetExplorer",
    "rights-dropped path uses token-information faking in `Secure_Init`",
]:
    require(srev_307, term, "SREV-307 adjacency")

for term in [
    "SECURE_ELEVATION_FLAGS_FAKE_ADMIN_ALLOWLIST",
    "No public Microsoft Win32 API page was found for `RtlQueryElevationFlags`",
    "No hook installation, image predicate",
    "Windows gate: IE Protected Mode / ActiveX install broker smoke",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-325",
    "owner: Sandboxie/core/dll/secure.c",
    "spec: docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.md",
    "schema: docs/plan/srev-325-secure-elevation-flags-fake-admin-allowlist.schema.json",
    "checker: docs/plan/check-srev-325.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-325: Secure Elevation Flags Fake Admin Allowlist",
    "SECURE_ELEVATION_FLAGS_FAKE_ADMIN_ALLOWLIST",
    "RtlQueryElevationFlags",
    "Secure_ShouldFakeRunningAsAdmin",
    "SynTPEnh.exe",
    "SREV-307",
]:
    require(ledger, term, "combined ledger")

print("SREV-325 schema/source gate passed")
