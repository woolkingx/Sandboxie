#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-269 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-269 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-269-file-firefox-exe-generic-write-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-269 failed: schema is not draft-07")
if schema.get("id") != "FILE_FIREFOX_EXE_GENERIC_WRITE_OWNER":
    raise SystemExit("SREV-269 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-269 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "GENERIC_WRITE is a broad file write-access mapping",
    "true-file fallback path where FileType exists",
    "DLL_IMAGE_MOZILLA_FIREFOX callers whose TruePath extension is exactly .exe",
    "FILE_DENIED_ACCESS zero gate still owns the decision",
    "comments and proof only; Firefox plugin compatibility still needs Windows runtime proof",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-269-file-firefox-exe-generic-write-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-269.md").read_text()

start = src.index("we don't have CopyPath, but if we did find TruePath")
end = src.index("having processed the exceptions", start)
fallback_block = src[start:end]

for term in [
    "if (FileType && (CreateDisposition == FILE_OPEN ||",
    "CreateDisposition == FILE_OPEN_IF))",
    "SREV-269: Firefox 106+ plugin executable probes can request the",
    "broad GENERIC_WRITE mapping for an existing true-path .exe.",
    "Strip only that generic write request before the true-file open",
    "decision so this branch cannot become a general write bypass.",
    "Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX && (DesiredAccess & GENERIC_WRITE)",
    "const WCHAR *dot = wcsrchr(TruePath, L'.');",
    "if (dot && _wcsicmp(dot, L\".exe\") == 0)",
    "DesiredAccess &= ~GENERIC_WRITE;",
]:
    require(fallback_block, term, "Firefox GENERIC_WRITE source block")

post_start = src.index("if ((DesiredAccess & FILE_DENIED_ACCESS) == 0)", start)
post_end = src.index("if (NT_SUCCESS(status)) TrueOpened = TRUE;", post_start)
true_file_gate = src[post_start:post_end]
for term in [
    "if ((DesiredAccess & FILE_DENIED_ACCESS) == 0)",
    "status = File_NtCreateTrueFile(",
]:
    require(true_file_gate, term, "true-file gate")

reject(fallback_block, "$Workaround$ - 3rd party fix", "Firefox GENERIC_WRITE source block")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-269: File Firefox Exe Generic Write Owner",
    "FILE_FIREFOX_EXE_GENERIC_WRITE_OWNER",
    "srev-269-file-firefox-exe-generic-write-owner.schema.json",
    "Sandboxie/core/dll/file.c",
    "DLL_IMAGE_MOZILLA_FIREFOX",
    "GENERIC_WRITE",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-269 source gate passed")
