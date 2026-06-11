#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-065 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-065-scm-sppsvc-handle-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-065 failed: schema is not draft-07")
if schema.get("id") != "SCM_SPPSVC_HANDLE_LIFETIME":
    raise SystemExit("SREV-065 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Handles returned by OpenSCManagerW and OpenServiceW are SCM/service object handles",
    "must be closed with CloseServiceHandle",
    "owns both handle1 and handle2 until its cleanup block",
    "assigned to the outer handle2 lifetime slot",
    "must not shadow the cleanup-owned service handle",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/scm_misc.c").read_text()
spec = (ROOT / "docs/plan/srev-065-scm-sppsvc-handle-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX int Scm_Start_Sppsvc()")
end = src.index("\n}", start) + 2
func = src[start:end]

for term in [
    "SC_HANDLE handle1 = Scm_OpenSCManagerW(NULL, NULL, GENERIC_READ);",
    "SC_HANDLE handle2 = NULL;",
    "handle2 = Scm_OpenServiceWImpl(handle1, L\"sppsvc\", SERVICE_START);",
    "Scm_StartServiceWImpl(handle2, 0, NULL);",
    "Scm_QueryServiceStatusImpl(handle2, &lpServiceStatus);",
    "Scm_CloseServiceHandleImpl(handle1);",
    "Scm_CloseServiceHandleImpl(handle2);",
]:
    require(func, term, "Scm_Start_Sppsvc source")

if "SC_HANDLE handle2 = Scm_OpenServiceWImpl" in func:
    raise SystemExit("SREV-065 failed: nested handle2 shadow remains")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openscmanagerw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew",
    "https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-closeservicehandle",
    "srev-065-scm-sppsvc-handle-lifetime.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-065: SCM Sppsvc Handle Lifetime",
    "SCM_SPPSVC_HANDLE_LIFETIME",
    "srev-065-scm-sppsvc-handle-lifetime.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-065 schema/source gate passed")
