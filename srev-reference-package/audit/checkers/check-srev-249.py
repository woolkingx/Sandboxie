#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-249 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-249 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-249-digitalguardian-comment-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-249 failed: schema is not draft-07")
if schema.get("id") != "DIGITALGUARDIAN_COMMENT_TOPOLOGY":
    raise SystemExit("SREV-249 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "module-presence evidence not module ownership",
    "DllMain may seed the flag",
    "DigitalGuardian_Init updates the same flag",
    "file.c owns Digital Guardian file-policy compatibility branches",
    "must not change detection loader callback file-policy branch conditions or return values",
]:
    require(contracts, term, "schema")

dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
dll_h = (ROOT / "Sandboxie/core/dll/dll.h").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-249-digitalguardian-comment-topology.md").read_text()
srev_088 = (ROOT / "docs/plan/srev-088-dll-digitalguardian-module-flag.md").read_text()
srev_088_schema = (
    ROOT / "docs/plan/srev-088-dll-digitalguardian-module-flag.schema.json"
).read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-249.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Digital Guardian module-presence flag; not a reference owner.",
    "Seed Digital Guardian presence if its DLL is already mapped before",
    "Sandboxie's loader callback observes it.",
    "Dll_DigitalGuardian = GetModuleHandleA(\"DgApi64.dll\");",
    "Dll_DigitalGuardian = GetModuleHandleA(\"DgApi.dll\");",
]:
    require(dllmain, term, "dllmain.c")

for term in [
    "Digital Guardian blocks direct true-file checks for write/closed",
    "paths, so delete-on-close treats the true file as absent.",
    "Without Digital Guardian, query true-file attributes directly;",
    "the Digital Guardian path uses the matched-path fallback below.",
    "Loader callback for the Digital Guardian module-presence flag.",
    "_FX BOOLEAN DigitalGuardian_Init(HMODULE hModule)",
    "Dll_DigitalGuardian = hModule;",
]:
    require(file_src, term, "file.c")

for needle in [
    "// $Workaround$ - 3rd party fix\nHMODULE Dll_DigitalGuardian = NULL;",
    "// $Workaround$ - 3rd party fix\n#ifdef _WIN64",
]:
    reject(dllmain, needle, "dllmain.c Digital Guardian site")

for needle in [
    "// $Workaround$ - 3rd party fix\n            if (Dll_DigitalGuardian",
    "// $Workaround$ - 3rd party fix\n            else if (!Dll_DigitalGuardian)",
    "// $Workaround$ - 3rd party fix\n_FX BOOLEAN DigitalGuardian_Init",
]:
    reject(file_src, needle, "file.c Digital Guardian site")

for term in [
    "Digital Guardian module-presence compatibility flag.",
    "extern HMODULE Dll_DigitalGuardian;",
]:
    require(dll_h, term, "dll.h SREV-088 adjacency")

for term in [
    "{ L\"dgapi64.dll\",           DigitalGuardian_Init,           0}",
    "{ L\"dgapi.dll\",             DigitalGuardian_Init,           0}",
]:
    require(ldr, term, "ldr.c callback wiring")

require(srev_088_schema, "DLL_DIGITALGUARDIAN_MODULE_FLAG", "SREV-088 schema adjacency")

for term in [
    "GetModuleHandleA(\"DgApi64.dll\" / \"DgApi.dll\")",
    "DigitalGuardian_Init when module loads",
]:
    require(srev_088, term, "SREV-088 adjacency")

for term in [
    "### SREV-249: Digital Guardian Comment Topology",
    "DIGITALGUARDIAN_COMMENT_TOPOLOGY",
    "srev-249-digitalguardian-comment-topology.schema.json",
    "Sandboxie/core/dll/dllmain.c",
    "Sandboxie/core/dll/file.c",
    "GetModuleHandleA",
    "DllMain",
    "SREV-088",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-249 source gate passed")
