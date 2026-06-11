---
kind: srev-ledger-entry
id: SREV-061
title: GDI Printer Retry Device Name Boundary
status: patched-source-level-after-official-createdcw-openprinter2-documentproperties-sh
owner: Sandboxie/core/dll/gdi.c
spec: docs/plan/srev-061-gdi-printer-device-name.md
schema: docs/plan/srev-061-gdi-printer-device-name.schema.json
checker: docs/plan/check-srev-061.py
runtime_gate: "32-bit WINSPOOL `CreateDCW` retry after SplWow64 failure, successful initial `CreateDCW` unchanged, and no spooler workaround when printer device name is absent"
---
### SREV-061: GDI Printer Retry Device Name Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official CreateDCW/OpenPrinter2/DocumentProperties shape and local WINSPOOL retry analysis; needs Windows 32-bit SplWow64 printer runtime proof |
| Evidence | `Sandboxie/core/dll/gdi.c` `Gdi_CreateDCW2` has a WINSPOOL retry workaround for failed 32-bit printer `CreateDCW` calls after SplWow64 termination. The retry path passed `lpInitData` to `OpenPrinter2W` and `DocumentProperties` as if it were a printer/device name. Microsoft documents `CreateDCW` `pwszDevice`/`lpszDevice` as the printer device name and `pdm`/`lpInitData` as `DEVMODEW*` initialization data. `OpenPrinter2W` and `DocumentProperties` require printer/device name strings. |
| Data | `lpszDriver`, `lpszDevice`, `lpszOutput`, `lpInitData`, printer handle, `DocumentProperties` device name, and retry `CreateDCW` result. |
| Schema | `GDI_PRINTER_RETRY_DEVICE_NAME` says printer identity flows from `CreateDCW` `lpszDevice` into `OpenPrinter2W` `pPrinterName` and `DocumentProperties` `pDeviceName`; `lpInitData` remains only `DEVMODEW*` initialization data for `CreateDCW`. |
| Topology | `CreateDCW` printer-name input crosses into the spooler object-open path, then `DocumentProperties` is used to wake/query the same printer before retrying `CreateDCW`. |
| Logic Risk | Treating a `DEVMODEW*` as a null-terminated printer-name string can make the workaround fail, read invalid memory as a name, or open the wrong spooler object. |
| Official Shape | `docs/plan/srev-061-gdi-printer-device-name.md` records Microsoft `CreateDCW`, `OpenPrinter2`, and `DocumentProperties` references. `docs/plan/srev-061-gdi-printer-device-name.schema.json` records the JSON Schema draft-07 local `GDI_PRINTER_RETRY_DEVICE_NAME` contract. |
| Fix | The WINSPOOL retry path now requires `lpszDevice`, passes `lpszDevice` to `OpenPrinter2W`, passes `lpszDevice` to `DocumentProperties`, and keeps `lpInitData` only for the `CreateDCW` call. |
| Acceptance Gate | `docs/plan/check-srev-061.py` validates the draft-07 schema, official references, required `lpszDevice` gate, `OpenPrinter2W(lpszDevice, ...)`, `DocumentProperties(..., lpszDevice, ...)`, removal of the `lpInitData` printer-name misuse, and ledger entry; `docs/plan/check-srev-061.sh` is the matrix wrapper. Windows gate: 32-bit WINSPOOL `CreateDCW` retry after SplWow64 failure, successful initial `CreateDCW` unchanged, and no spooler workaround when printer device name is absent. |
