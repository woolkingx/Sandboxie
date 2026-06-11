# SREV-287: GDI SplWow64 Printer DC Retry Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/gdi.c`, `Sandboxie/core/dll/ldr.c`, SREV-061, Microsoft CreateDCW/OpenPrinter2/DocumentProperties/SplWow64 references |
| Output artifact | Source and loader-registration comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gdi_CreateDCW2` 32-bit WINSPOOL printer DC retry path |
| Acceptance gate | Targeted checker validates official references, source comment, SREV-061 adjacency, unchanged retry behavior, stale wording removal, and ledger fragment |

## Data

`Gdi_CreateDCW2` is the 32-bit printer DC retry wrapper for:

```text
lpszDriver == WINSPOOL
lpszDevice printer name
lpszOutput
lpInitData DEVMODEW initialization data
SplWow64 bridge state
OpenPrinter2W printer handle
DocumentPropertiesW printer-name query edge
retry CreateDCW result
```

SREV-061 already fixed the source-level API-shape bug in this block by keeping
`lpInitData` as DEVMODE data and routing printer identity through `lpszDevice`.
The remaining `Gdi_CreateDCW2` source comment still described the branch as a
possible generic workaround, which hid the already documented owner boundary.
After the first SREV-287 pass, the `winspool.drv` loader registration comment
still used generic print-spooler workaround wording.

## Official Shape

Microsoft documents `CreateDCW` as creating a device context for a named device.
For printer devices, `pwszDevice` is the output device name and `pdm` is a
`DEVMODEW*` with device-specific initialization data.

Microsoft documents `OpenPrinter2` as opening a printer by null-terminated
printer or print-server name.

Microsoft documents `DocumentProperties` as taking an opened printer handle and
`pDeviceName`; with `fMode == 0`, it queries the required DEVMODE size.

Microsoft documents that 64-bit Windows supports printing from 32-bit processes
through `Splwow64.exe`, which can load 64-bit printer drivers for the 32-bit
caller.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdcw`
- `https://learn.microsoft.com/en-us/windows/win32/printdocs/openprinter2`
- `https://learn.microsoft.com/en-us/windows/win32/printdocs/documentproperties`
- `https://learn.microsoft.com/en-us/troubleshoot/windows/win32/print-app-xps-document-writer`

## Schema

Local schema:

```text
docs/plan/srev-287-gdi-splwow64-printer-dc-retry-owner.schema.json
```

Contract id:

```text
GDI_SPLWOW64_PRINTER_DC_RETRY_OWNER
```

## Boundary

```text
CreateDCW(WINSPOOL, lpszDevice, lpszOutput, lpInitData)
  -> initial native CreateDCW
  -> failed printer DC creation
  -> lpszDevice gate
  -> OpenPrinter2W(lpszDevice)
  -> DocumentPropertiesW(..., lpszDevice, fMode=0)
  -> bounded retry of the same CreateDCW request
```

SREV-061 owns the source-level API shape for this boundary. This SREV owns the
source comment topology and the `winspool.drv -> Gdi_Init_Spool` loader
registration comment so future edits do not treat the branch as an unbounded
compatibility bucket.

## Topology

```text
32-bit process on 64-bit Windows
  -> WINSPOOL printer DC request
  -> SplWow64 print-driver host bridge
  -> Sandboxie Gdi_CreateDCW2 retry path
  -> printer-name wake/query edge
  -> same CreateDCW request
```

## Logic Risk

The old wording made the code look like an anonymous retry loop rather than a
bounded SplWow64/WINSPOOL owner path. That can misroute future patches into
broadening the retry, removing the SREV-061 device-name gate, or treating
`lpInitData` as a printer identity again.

## Fix

Comment-only source clarification. The source now names SREV-287, the 32-bit
WINSPOOL to SplWow64 bridge, and the SREV-061 `lpszDevice` /
`DocumentProperties` gate. The loader registration now names the same SREV-287
32-bit WINSPOOL/SplWow64 printer DC retry owner. No retry count, delay, native
call, spooler call, or hook registration changed.

Source gate phrase: No retry count, delay, native call, spooler call, or hook
registration changed.

## Acceptance Gate

`docs/plan/check-srev-287.py` validates the draft-07 schema, official
references, source comment, loader registration comment, SREV-061 adjacency,
unchanged `Gdi_CreateDCW2` retry behavior, stale workaround wording removal
from the function and loader entry, combined ledger entry, and split ledger
fragment.

Runtime gate is inherited from SREV-061: Windows 32-bit WINSPOOL `CreateDCW`
retry after SplWow64 failure, successful initial `CreateDCW` unchanged, and no
spooler path when no printer device name is supplied.
