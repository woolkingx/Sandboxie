#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-098 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-098-ie-embedding-clsid-registry-policy.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-098 failed: schema is not draft-07")
if schema.get("id") != "IE_EMBEDDING_CLSID_REGISTRY_POLICY":
    raise SystemExit("SREV-098 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "RegNtPreCreateKeyEx and RegNtPreOpenKeyEx",
    "registry lookup denial policy, not a process launch owner",
    "local InternetExplorer CLSID",
    "selected host callers where proc is NULL",
    "winword.exe, powerpnt.exe, excel.exe, explorer.exe, and svchost.exe",
    "returns STATUS_ACCESS_DENIED before ordinary sandbox key redirection",
    "CompleteName matcher and remains null-safe",
    "Key_MyParseProc_2",
]:
    require(contracts, term, "schema")

key_flt = (ROOT / "Sandboxie/core/drv/key_flt.c").read_text()
util = (ROOT / "Sandboxie/core/drv/util.c").read_text()
ieserver = (ROOT / "Sandboxie/core/svc/comserver9_ie.c").read_text()
comserver = (ROOT / "Sandboxie/core/svc/comserver9.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
spec = (ROOT / "docs/plan/srev-098-ie-embedding-clsid-registry-policy.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "CmRegisterCallbackEx",
    "Key_Callback, &Driver_Altitude",
    "RegNtPreCreateKeyEx",
    "RegNtPreOpenKeyEx",
    "REG_OPEN_CREATE_KEY_INFORMATION_VISTA *Info;",
    "Info = (REG_OPEN_CREATE_KEY_INFORMATION_VISTA *)Arg2;",
    "BlockIEEmbedding policy: hide the InternetExplorer COM class",
    "selected host callers",
    "IE server path",
    "process-launch forcing",
    "SearchUnicodeString(Info->CompleteName, L\"CLSID\\\\{0002df01-0000-0000-c000-000000000046}\", TRUE)",
    "Conf_Get_Boolean(NULL, L\"BlockIEEmbedding\", 0, FALSE)",
    "if (!proc)",
    "_wcsicmp(nptr, L\"winword.exe\")",
    "_wcsicmp(nptr, L\"powerpnt.exe\")",
    "_wcsicmp(nptr, L\"excel.exe\")",
    "_wcsicmp(nptr, L\"explorer.exe\")",
    "_wcsicmp(nptr, L\"svchost.exe\")",
    "status = STATUS_ACCESS_DENIED;",
    "if (status != STATUS_SUCCESS)",
    "if (!proc || proc->bHostInject || proc->disable_key_flt)",
    "return Key_MyParseProc_2(",
]:
    require(key_flt, term, "key_flt.c policy shape")

if "HACK ALERT!" in key_flt:
    raise SystemExit("SREV-098 failed: stale HACK ALERT remains")

if key_flt.index("if (status != STATUS_SUCCESS)") > key_flt.index("if (!proc || proc->bHostInject || proc->disable_key_flt)"):
    raise SystemExit("SREV-098 failed: denial does not happen before host/sandbox bypass")

for term in [
    "SearchUnicodeString(PCUNICODE_STRING pString1",
    "pString1 == NULL",
    "pString1->Buffer == NULL",
    "pString1->Length == 0",
    "pString2 == NULL",
]:
    require(util, term, "SearchUnicodeString null-safe matcher")

for term in [
    "// {0002DF01-0000-0000-C000-000000000046}",
    "static const GUID CLSID_InternetExplorer",
    "0x0002DF01, 0x0000, 0x0000",
]:
    require(ieserver, term, "local InternetExplorer CLSID identity")

for term in [
    "for objects with CLSID_InternetExplorer",
    "pClsid = &CLSID_InternetExplorer;",
    "pMyCreateInstance = IEServer_MyCreateInstance;",
]:
    require(comserver, term, "local IE COM server topology")

for term in [
    "[BlockIEEmbedding]",
    "Controls whether Sandboxie should allow Internet Explorer (IE) web browser embedding",
]:
    require(settings, term, "BlockIEEmbedding setting")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "RegistryCallback",
    "non-success",
    "`NTSTATUS`",
    "RegNtPreCreateKeyEx",
    "REG_CREATE_KEY_INFORMATION_V1",
    "COM class registration",
    "`-Embedding`",
    "IWebBrowser2",
    "No runtime behavior was changed.",
]:
    require(spec, term, "spec official shape")

for term in [
    "### SREV-098: IE Embedding CLSID Registry Policy",
    "IE_EMBEDDING_CLSID_REGISTRY_POLICY",
    "srev-098-ie-embedding-clsid-registry-policy.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-098 schema/source gate passed")
