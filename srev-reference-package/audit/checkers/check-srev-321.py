#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-321 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-321 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-321-proc-msi-systemless-process-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-321 failed: schema is not draft-07")
if schema.get("id") != "PROC_MSI_SYSTEMLESS_PROCESS_GATE":
    raise SystemExit("SREV-321 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/proc.c":
    raise SystemExit("SREV-321 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "MSI systemless state is owned by scm_msi.c",
    "process creation token and security-attributes selection",
    "DLL_IMAGE_MSI_INSTALLER, Scm_MsiServer_Systemless",
    "not RunServicesAsSystem",
    "not MsiInstallerExemptions",
    "clearing hToken and lpProcessAttributes must stay local",
    "SREV-092 owns MSI in-use event lifetime",
    "SREV-270 owns the Config.Msi file retry",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
scm_msi = (ROOT / "Sandboxie/core/dll/scm_msi.c").read_text()
spec = (ROOT / "docs/plan/srev-321-proc-msi-systemless-process-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-321.md").read_text()
srev_092 = (ROOT / "docs/plan/ledger/srev-092.md").read_text()
srev_270 = (ROOT / "docs/plan/ledger/srev-270.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = proc.index("// OriginalToken BEGIN")
end = proc.index("TlsData->proc_create_process_fake_admin", start)
msi_block = proc[start:end]

for term in [
    "extern BOOLEAN Scm_MsiServer_Systemless;",
    "if (Dll_ImageType == DLL_IMAGE_MSI_INSTALLER && Scm_MsiServer_Systemless",
    "&& !SbieApi_QueryConfBool(NULL, L\"RunServicesAsSystem\", FALSE) && !SbieApi_QueryConfBool(NULL, L\"MsiInstallerExemptions\", FALSE)) {",
    "SREV-321: systemless MSI server child process creation gate.",
    "Existing predicate clears token and process security attributes only here.",
    "hToken = NULL;",
    "lpProcessAttributes = NULL;",
]:
    require(msi_block, term, "Proc_CreateProcessInternalW MSI block")

reject(msi_block, "simple workaround", "Proc_CreateProcessInternalW MSI comment")

for term in [
    "BOOLEAN Scm_MsiServer_Systemless = FALSE;",
    "Scm_MsiServer_Systemless = TRUE;",
    "To run MSIServer without system privileges",
    "Scm_MsiDll",
]:
    require(scm_msi, term, "scm_msi systemless owner")

for term in [
    "SCM_MSI_LOADER_UNLOAD_EVENT_OWNER",
    "MSI in-use event lifetime",
    "SREV-270",
]:
    require(srev_092 + ledger, term, "MSI adjacency")

for term in [
    "FILE_MSI_CONFIG_MSI_QUERY_DIRECTORY_RETRY",
    "Config.Msi",
    "DLL_IMAGE_MSI_INSTALLER",
]:
    require(srev_270, term, "SREV-270 adjacency")

for term in [
    "PROC_MSI_SYSTEMLESS_PROCESS_GATE",
    "`CreateProcessInternalW` is not the public Microsoft API contract",
    "SREV-092 owns MSI in-use event lifetime",
    "SREV-270 owns the Config.Msi file",
    "No token value, process-attributes value, predicate",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-321",
    "owner: Sandboxie/core/dll/proc.c",
    "spec: docs/plan/srev-321-proc-msi-systemless-process-gate.md",
    "schema: docs/plan/srev-321-proc-msi-systemless-process-gate.schema.json",
    "checker: docs/plan/check-srev-321.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-321: Proc MSI Systemless Process Gate",
    "PROC_MSI_SYSTEMLESS_PROCESS_GATE",
    "Scm_MsiServer_Systemless",
    "RunServicesAsSystem",
    "MsiInstallerExemptions",
]:
    require(ledger, term, "combined ledger")

print("SREV-321 schema/source gate passed")
