#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-193 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-193 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-193-ie-com-navigation-input-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-193 failed: schema is not draft-07")
if schema.get("id") != "IE_COM_NAVIGATION_INPUT_CONTRACT":
    raise SystemExit("SREV-193 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/comserver9_ie.c":
    raise SystemExit("SREV-193 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "IWebBrowser2::Navigate URL is a required BSTR",
    "IWebBrowser2::Navigate2 URL is a VARIANT pointer",
    "local Navigate2 support is VT_BSTR only",
    "VARIANT vt must be checked before reading bstrVal",
    "navigation string inputs must be non-NULL before restart",
    "IUri_GetRawUri output BSTR is caller-owned",
    "IUri_GetRawUri output is released with SysFreeString",
    "SboxSvc links OleAut32.lib when SysFreeString is used",
]:
    require(contracts, term, "schema contracts")

ie = (ROOT / "Sandboxie/core/svc/comserver9_ie.c").read_text()
server = (ROOT / "Sandboxie/core/svc/comserver9.c").read_text()
vcxproj = (ROOT / "Sandboxie/core/svc/SboxSvc.vcxproj").read_text()
spec = (ROOT / "docs/plan/srev-193-ie-com-navigation-input-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-193.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

exec_block = between(
    ie,
    "_FX HRESULT IEServer_IOleCommandTarget_Exec(",
    "//---------------------------------------------------------------------------\n// IEServer_ITargetFramePriv_FindFrameDownwards",
)
for term in [
    "pvaIn->vt != VT_BSTR || (! pvaIn->bstrVal)",
    "IEServer_RestartProgram(pvaIn->bstrVal);",
]:
    require(exec_block, term, "IOleCommandTarget Exec BSTR gate")

navigate_hack = between(
    ie,
    "_FX HRESULT IEServer_ITargetFramePriv_NavigateHack(",
    "//---------------------------------------------------------------------------\n// IEServer_ITargetFramePriv_FindBrowserByIndex",
)
require(navigate_hack, "if (! pszUrl)\n        return E_INVALIDARG;", "NavigateHack URL gate")
require(navigate_hack, "IEServer_RestartProgram(pszUrl);", "NavigateHack restart")

aggregated = between(
    ie,
    "_FX HRESULT IEServer_ITargetFramePriv2_AggregatedNavigation2(",
    "//---------------------------------------------------------------------------\n// IEServer_IWebBrowser2_NotImpl",
)
for term in [
    "BSTR pszUrl = NULL;",
    "if (! pUri)\n        return E_INVALIDARG;",
    "hr = IUri_GetRawUri(pUri, &pszUrl);",
    "SysFreeString(pszUrl);",
]:
    require(aggregated, term, "AggregatedNavigation2 IUri ownership")
if not (
    aggregated.index("if (! pUri)")
    < aggregated.index("hr = IUri_GetRawUri(pUri, &pszUrl);")
    < aggregated.index("SysFreeString(pszUrl);")
):
    raise SystemExit("SREV-193 failed: AggregatedNavigation2 ownership order is wrong")

navigate = between(
    ie,
    "_FX HRESULT IEServer_IWebBrowser2_Navigate(",
    "//---------------------------------------------------------------------------\n// IEServer_IWebBrowser2_put_Visible",
)
require(navigate, "if (! url)\n        return E_INVALIDARG;", "Navigate URL gate")
require(navigate, "IEServer_RestartProgram(url);", "Navigate restart")

navigate2 = between(
    ie,
    "_FX HRESULT IEServer_IWebBrowser2_Navigate2(",
    "//---------------------------------------------------------------------------\n// IEServer_ITargetFrame2_NotImpl",
)
for term in [
    "if ((! URL) || URL->vt != VT_BSTR || (! URL->bstrVal))",
    "return E_INVALIDARG;",
    "IEServer_RestartProgram(URL->bstrVal);",
]:
    require(navigate2, term, "Navigate2 variant gate")
if not navigate2.index("URL->vt != VT_BSTR") < navigate2.index("URL->bstrVal"):
    raise SystemExit("SREV-193 failed: Navigate2 reads bstrVal before vt gate")
if not navigate2.index("if ((! URL)") < navigate2.index("IEServer_RestartProgram(URL->bstrVal);"):
    raise SystemExit("SREV-193 failed: Navigate2 restart happens before variant gate")

set_frame_src = between(
    ie,
    "_FX HRESULT IEServer_ITargetFrame2_SetFrameSrc(",
    "//---------------------------------------------------------------------------\n// IEServer_IHlinkFrame_NotImpl",
)
require(set_frame_src, "if (! pszFrameSrc)\n        return E_INVALIDARG;", "SetFrameSrc URL gate")

restart = between(
    ie,
    "_FX void IEServer_RestartProgram(",
    "//---------------------------------------------------------------------------\n// IEServer_ResolveUrl",
)
require(restart, "if (! arg)\n        return;", "RestartProgram final NULL guard")
if not restart.index("if (! arg)") < restart.index("IEServer_ResolveUrl"):
    raise SystemExit("SREV-193 failed: RestartProgram guard is after string use")

require(server, "#include <oleauto.h>", "oleauto include")

dependency_lines = [
    line for line in vcxproj.splitlines()
    if "<AdditionalDependencies>" in line
]
if len(dependency_lines) != 8:
    raise SystemExit("SREV-193 failed: unexpected SboxSvc dependency block count")
for line in dependency_lines:
    require(line, "OleAut32.lib", "OleAut32 service dependency")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-193",
    "owner: Sandboxie/core/svc/comserver9_ie.c",
    "spec: docs/plan/srev-193-ie-com-navigation-input-contract.md",
    "schema: docs/plan/srev-193-ie-com-navigation-input-contract.schema.json",
    "checker: docs/plan/check-srev-193.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-193: IE COM Navigation Input Contract",
    "IE_COM_NAVIGATION_INPUT_CONTRACT",
    "Sandboxie/core/svc/comserver9_ie.c",
    "IWebBrowser2::Navigate2",
    "IUri::GetRawUri",
    "SysFreeString",
    "OleAut32.lib",
]:
    require(ledger, term, "combined ledger")

print("SREV-193 schema/source gate passed")
