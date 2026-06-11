#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-285 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-285 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-285-mso-recovery-module-signal-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-285 failed: schema is not draft-07")
if schema.get("id") != "MSO_RECOVERY_MODULE_SIGNAL_OWNER":
    raise SystemExit("SREV-285 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_recovery.c":
    raise SystemExit("SREV-285 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL load state is process-local module presence",
    "mso.dll callback publishes only File_MsoDllLoaded",
    "module-presence signal for the Office recovery filter",
    "File_IsRecoverable owns the Office temporary-file recovery classification",
    "applies only after RecoverFolder prefix match",
    "SREV-072 owns recoverable-path redirector normalization",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

file_recovery = (ROOT / "Sandboxie/core/dll/file_recovery.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-285-mso-recovery-module-signal-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-285.md").read_text()
srev_072 = (ROOT / "docs/plan/ledger/srev-072.md").read_text()

for term in [
    "static BOOLEAN File_MsoDllLoaded = FALSE;",
    "if (File_MsoDllLoaded) {",
    "ptr[1] == L'~' && ptr[2] == L'$'",
    "ptr = wcschr(ptr, L'.');",
    "if (! ptr)\n                    ok = FALSE;",
]:
    require(file_recovery, term, "File_IsRecoverable Office filter")

func_start = file_recovery.index("_FX BOOLEAN File_MsoDll(")
func_end = file_recovery.index("return TRUE;", func_start) + len("return TRUE;")
func = file_recovery[func_start:func_end]
for term in [
    "SREV-285: mso.dll is a module-presence signal for the",
    "Office recovery filter in File_IsRecoverable.",
    "File_MsoDllLoaded = TRUE;",
    "return TRUE;",
]:
    require(func, term, "File_MsoDll source")

reject(func, "hack for File_IsRecoverable", "File_MsoDll stale comment")

for term in [
    "{ L\"mso.dll\",               File_MsoDll,                    0}, // SREV-285: Office recovery filter signal",
]:
    require(ldr, term, "ldr module callback")
reject(ldr, "{ L\"mso.dll\",               File_MsoDll,                    0}, // hack for File_IsRecoverable", "ldr stale comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "MSO_RECOVERY_MODULE_SIGNAL_OWNER",
    "srev-285-mso-recovery-module-signal-owner.schema.json",
    "mso.dll",
    "File_MsoDllLoaded",
    "File_IsRecoverable",
    "SREV-072",
]:
    require(spec, term, "spec")

for term in [
    "FILE_RECOVERY_MUP_PATH_BUFFER",
    "File_IsRecoverable",
    "redirector normalization",
]:
    require(srev_072, term, "SREV-072 adjacency")

for term in [
    "### SREV-285: MSO Recovery Module Signal Owner",
    "MSO_RECOVERY_MODULE_SIGNAL_OWNER",
    "srev-285-mso-recovery-module-signal-owner.schema.json",
    "Sandboxie/core/dll/file_recovery.c",
    "Sandboxie/core/dll/ldr.c",
    "mso.dll",
    "File_IsRecoverable",
    "SREV-072",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-285 source gate passed")
