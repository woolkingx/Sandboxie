#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-088 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-088-dll-digitalguardian-module-flag.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-088 failed: schema is not draft-07")
if schema.get("id") != "DLL_DIGITALGUARDIAN_MODULE_FLAG":
    raise SystemExit("SREV-088 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "loaded-module presence evidence",
    "GetModuleHandleA in dllmain.c",
    "must not be used as a FreeLibrary-owned reference",
    "DigitalGuardian_Init remains",
    "file.c remains",
    "shared data role",
]:
    require(contracts, term, "schema")

dll_h = (ROOT / "Sandboxie/core/dll/dll.h").read_text()
dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-088-dll-digitalguardian-module-flag.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Digital Guardian module-presence compatibility flag.",
    "extern HMODULE Dll_DigitalGuardian;",
]:
    require(dll_h, term, "dll.h declaration")

if "$Workaround$ - 3rd party fix\nextern HMODULE Dll_DigitalGuardian;" in dll_h:
    raise SystemExit("SREV-088 failed: stale dll.h workaround wording remains")

for term in [
    "Dll_DigitalGuardian = GetModuleHandleA(\"DgApi64.dll\");",
    "Dll_DigitalGuardian = GetModuleHandleA(\"DgApi.dll\");",
]:
    require(dllmain, term, "dllmain.c module presence population")

for term in [
    "{ L\"dgapi64.dll\",           DigitalGuardian_Init,           0}",
    "{ L\"dgapi.dll\",             DigitalGuardian_Init,           0}",
]:
    require(ldr, term, "ldr.c loader consumer")

for term in [
    "_FX BOOLEAN DigitalGuardian_Init(HMODULE hModule)",
    "if (Dll_DigitalGuardian && (PATH_IS_WRITE(mp_flags) || PATH_IS_CLOSED(mp_flags)))",
    "else if (!Dll_DigitalGuardian)",
]:
    require(file_src, term, "file.c policy consumer")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-088: DLL Digital Guardian Module Flag",
    "DLL_DIGITALGUARDIAN_MODULE_FLAG",
    "srev-088-dll-digitalguardian-module-flag.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-088 schema/source gate passed")
