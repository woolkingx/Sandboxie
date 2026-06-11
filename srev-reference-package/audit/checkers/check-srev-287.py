#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-287 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-287 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-287-gdi-splwow64-printer-dc-retry-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-287 failed: schema is not draft-07")
if schema.get("id") != "GDI_SPLWOW64_PRINTER_DC_RETRY_OWNER":
    raise SystemExit("SREV-287 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/gdi.c":
    raise SystemExit("SREV-287 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gdi_CreateDCW2 owns only the 32-bit WINSPOOL printer DC retry path",
    "SREV-061 owns the lpszDevice printer-name and lpInitData DEVMODE separation",
    "the Gdi_CreateDCW2 source comment must name the SplWow64 printer-host bridge and SREV-061 gate rather than a generic workaround",
    "the winspool.drv loader registration comment must name the SREV-287 32-bit WINSPOOL/SplWow64 printer DC retry owner",
    "the retry remains bounded by WINSPOOL driver match lpszDevice presence DocumentProperties availability and retry count",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/gdi.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-287-gdi-splwow64-printer-dc-retry-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-287.md").read_text()
srev_061 = (ROOT / "docs/plan/ledger/srev-061.md").read_text()

start = source.index("_FX HDC Gdi_CreateDCW2(")
end = source.index("// Gdi_CreateDCA", start)
func = source[start:end]

for term in [
    "SREV-287: 32-bit WINSPOOL CreateDCW crosses the SplWow64",
    "print-driver host on 64-bit Windows.",
    "retry the same printer DC",
    "request through the SREV-061 lpszDevice/DocumentProperties gate.",
    "HDC hdc = __sys_CreateDCW(\n                        lpszDriver, lpszDevice, lpszOutput, lpInitData);",
    "if ((! hdc) && lpszDriver && lpszDevice && _wcsicmp(lpszDriver, L\"WINSPOOL\") == 0)",
    "while (__sys_DocumentProperties && (! hdc) && (retry < 20))",
    "Sleep(retry * 25);",
    "if (! __sys_OpenPrinter2W(lpszDevice, &hPrinter, NULL, NULL))",
    "__sys_DocumentProperties(\n                NULL, hPrinter, lpszDevice, NULL, NULL, 0);",
    "hdc = __sys_CreateDCW(\n                        lpszDriver, lpszDevice, lpszOutput, lpInitData);",
    "__sys_ClosePrinter(hPrinter);",
]:
    require(func, term, "Gdi_CreateDCW2 source")

for stale in [
    "it seems a possible workaround",
    "times, until the CreateDC call finally works",
]:
    reject(func, stale, "Gdi_CreateDCW2 comment")

for term in [
    "{ L\"winspool.drv\",          Gdi_Init_Spool,                 0}, // SREV-287: 32-bit WINSPOOL/SplWow64 printer DC retry",
]:
    require(ldr, term, "loader registration")
reject(ldr, "winspool.drv\",          Gdi_Init_Spool,                 0}, // print spooler workaround for 32 bit", "loader comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GDI_SPLWOW64_PRINTER_DC_RETRY_OWNER",
    "SplWow64",
    "CreateDCW",
    "OpenPrinter2",
    "DocumentProperties",
    "SREV-061",
    "loader registration",
    "No retry count, delay, native call, spooler call, or",
]:
    require(spec, term, "spec")

for term in [
    "GDI_PRINTER_RETRY_DEVICE_NAME",
    "lpszDevice",
    "lpInitData",
    "DEVMODE",
    "OpenPrinter2W",
    "DocumentProperties",
]:
    require(srev_061, term, "SREV-061 adjacency")

for term in [
    "### SREV-287: GDI SplWow64 Printer DC Retry Owner",
    "GDI_SPLWOW64_PRINTER_DC_RETRY_OWNER",
    "srev-287-gdi-splwow64-printer-dc-retry-owner.schema.json",
    "Sandboxie/core/dll/gdi.c",
    "Gdi_CreateDCW2",
    "Gdi_Init_Spool",
    "SplWow64",
    "SREV-061",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-287 source gate passed")
