#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-179 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-179 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-179 failed: {label}")


def function_slice(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


schema = json.loads((ROOT / "docs/plan/srev-179-config-ansi-list-exact-match.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-179 failed: schema is not draft-07")
if schema.get("id") != "CONFIG_ANSI_LIST_EXACT_MATCH":
    raise SystemExit("SREV-179 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SbieDll_CheckStringInListA owns ANSI caller-string membership checks",
    "both strings reach their terminator at the same position",
    "A shorter wide config entry is not a match for a longer ANSI caller string",
    "A shorter ANSI caller string is not a match for a longer wide config entry",
    "preserves the existing case-sensitive comparison behavior",
    "preserves SbieApi_QueryConfAsIs iteration and STATUS_BUFFER_TOO_SMALL skip behavior",
]:
    require(contracts, term, "schema contracts")

config = (ROOT / "Sandboxie/core/dll/config.c").read_text()
dllhook = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
spec = (ROOT / "docs/plan/srev-179-config-ansi-list-exact-match.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-179.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

wide_func = function_slice(
    config,
    "BOOLEAN SbieDll_CheckStringInList(const WCHAR* string",
    "//---------------------------------------------------------------------------\n// SbieDll_CheckStringInListA",
)
ansi_helper = function_slice(
    config,
    "static BOOLEAN Config_IsEqualAnsiString",
    "BOOLEAN SbieDll_CheckStringInListA",
)
ansi_func = function_slice(
    config,
    "BOOLEAN SbieDll_CheckStringInListA",
    "//---------------------------------------------------------------------------\n// SbieDll_CheckStringInList\n//---------------------------------------------------------------------------\n\n\nBOOLEAN SbieDll_CheckPatternInList",
)

for term in [
    "if (_wcsicmp(buf, string) == 0)",
    "SbieApi_QueryConfAsIs(boxname, setting, index, buf, 64 * sizeof(WCHAR))",
]:
    require(wide_func, term, "wide exact-match precedent")

for term in [
    "while (*wide && *ansi && *wide == (WCHAR)(UCHAR)*ansi)",
    "++wide;",
    "++ansi;",
    "return (*wide == L'\\0' && *ansi == '\\0');",
]:
    require(ansi_helper, term, "ANSI exact-match helper")

for term in [
    "SbieApi_QueryConfAsIs(boxname, setting, index, buf, 64 * sizeof(WCHAR))",
    "if (Config_IsEqualAnsiString(buf, string))",
    "return TRUE;",
    "else if (status != STATUS_BUFFER_TOO_SMALL)",
]:
    require(ansi_func, term, "ANSI list helper")

reject(
    ansi_func,
    "for (const char* tmp = string; *ptr && *tmp && *ptr == *tmp; ptr++, tmp++);",
    "stale prefix loop",
)
reject(ansi_func, "if (*ptr == L'\\0')", "stale wide-only terminator gate")
assert_before(
    ansi_func,
    "query before exact helper",
    "SbieApi_QueryConfAsIs(boxname, setting, index, buf, 64 * sizeof(WCHAR))",
    "Config_IsEqualAnsiString(buf, string)",
)

for term in [
    "SbieDll_CheckStringInListA(name, NULL, L\"ApiSkipTrace\")",
    "if (!SbieDll_CheckStringInList(ModuleName, NULL, L\"ApiTraceDll\"))",
]:
    require(dllhook, term, "caller evidence")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-179",
    "owner: SbieDll_CheckStringInListA config-list membership helper",
    "checker: docs/plan/check-srev-179.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-179: Config ANSI List Exact Match",
    "CONFIG_ANSI_LIST_EXACT_MATCH",
    "Sandboxie/core/dll/config.c",
    "Sandboxie/core/dll/dllhook.c",
    "Config_IsEqualAnsiString",
    "SbieDll_CheckStringInListA",
    "ApiSkipTrace",
]:
    require(ledger, term, "ledger")

print("SREV-179 schema/source gate passed")
