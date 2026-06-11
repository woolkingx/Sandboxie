#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-061 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-061-gdi-printer-device-name.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-061 failed: schema is not draft-07")
if schema.get("id") != "GDI_PRINTER_RETRY_DEVICE_NAME":
    raise SystemExit("SREV-061 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "pwszDevice is the printer device name",
    "pdm is DEVMODE initialization data and is not a printer-name string",
    "OpenPrinter2W pPrinterName must receive the printer",
    "DocumentProperties pDeviceName must receive the device name",
    "require lpszDevice before opening the spooler object",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/gdi.c").read_text()
spec = (ROOT / "docs/plan/srev-061-gdi-printer-device-name.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX HDC Gdi_CreateDCW2(")
end = src.index("// Gdi_CreateDCA", start)
func = src[start:end]

for term in [
    "if ((! hdc) && lpszDriver && lpszDevice && _wcsicmp(lpszDriver, L\"WINSPOOL\") == 0)",
    "if (! __sys_OpenPrinter2W(lpszDevice, &hPrinter, NULL, NULL))",
    "__sys_DocumentProperties(\n                NULL, hPrinter, lpszDevice, NULL, NULL, 0);",
    "hdc = __sys_CreateDCW(\n                        lpszDriver, lpszDevice, lpszOutput, lpInitData);",
]:
    require(func, term, "Gdi_CreateDCW2 source")

for bad in [
    "__sys_OpenPrinter2W(lpInitData",
    "hPrinter, lpInitData",
]:
    if bad in func:
        raise SystemExit(f"SREV-061 failed: stale DEVMODE-as-printer-name call remains: {bad}")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdcw",
    "https://learn.microsoft.com/en-us/windows/win32/printdocs/openprinter2",
    "https://learn.microsoft.com/en-us/windows/win32/printdocs/documentproperties",
    "srev-061-gdi-printer-device-name.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-061: GDI Printer Retry Device Name Boundary",
    "GDI_PRINTER_RETRY_DEVICE_NAME",
    "srev-061-gdi-printer-device-name.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-061 schema/source gate passed")
