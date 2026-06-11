# SREV-061: GDI Printer Retry Device Name Boundary

## Data

`Sandboxie/core/dll/gdi.c` has a 32-bit printer DC retry workaround for
`CreateDCW(WINSPOOL, ...)` after a failed first attempt.

The relevant data nodes are:

```text
lpszDriver
lpszDevice
lpszOutput
lpInitData
printer handle
DocumentProperties device name
retry CreateDCW result
```

## Official Shape

Microsoft documents `CreateDCW` as taking a printer device name in `pwszDevice`
and device-specific initialization data in `pdm`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdcw
```

Microsoft documents `OpenPrinter2` as taking `pPrinterName`, a null-terminated
printer or print-server name:

```text
https://learn.microsoft.com/en-us/windows/win32/printdocs/openprinter2
```

Microsoft documents `DocumentProperties` as taking `pDeviceName`, a
null-terminated device name, plus optional `DEVMODE` input/output buffers:

```text
https://learn.microsoft.com/en-us/windows/win32/printdocs/documentproperties
```

## Schema

Local schema:

```text
docs/plan/srev-061-gdi-printer-device-name.schema.json
```

Printer identity and printer initialization data are separate fields:

```text
CreateDCW pwszDevice -> OpenPrinter2 pPrinterName -> DocumentProperties pDeviceName
CreateDCW pdm -> CreateDCW lpInitData only
```

## Topology

```text
CreateDCW printer-name input -> spooler printer handle -> DocumentProperties wake-up -> retry CreateDCW
```

The retry path may touch the print spooler only when it has a printer device
name. It must not reinterpret a `DEVMODEW*` as a printer-name string.

## Logic Risk

Before this patch, the retry workaround passed `lpInitData` to
`OpenPrinter2W` and `DocumentProperties` where both APIs require printer/device
name strings. `lpInitData` is the `DEVMODEW*` from `CreateDCW`. Treating it as a
string can fail the workaround, read invalid memory as a name, or open the wrong
spooler object.

## Fix

The WINSPOOL retry path now requires `lpszDevice` before entering the spooler
retry loop, passes `lpszDevice` to `OpenPrinter2W`, and passes `lpszDevice` to
`DocumentProperties`. `lpInitData` remains only the `CreateDCW` initialization
data.

## Acceptance Gate

`docs/plan/check-srev-061.py` validates the draft-07 schema, official reference
links, required `lpszDevice` gate, `OpenPrinter2W(lpszDevice, ...)`,
`DocumentProperties(..., lpszDevice, ...)`, and ledger entry.

Windows gate: 32-bit process on affected Windows/SplWow64 path should retry a
WINSPOOL `CreateDCW` failure using the actual printer name, preserve successful
initial `CreateDCW`, and skip the spooler workaround when no printer device name
is supplied.
