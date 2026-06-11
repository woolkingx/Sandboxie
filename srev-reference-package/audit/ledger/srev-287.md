---
kind: srev-ledger-entry
id: SREV-287
title: GDI SplWow64 Printer DC Retry Owner
status: patched-comment-topology-after-srev-061-and-official-splwow64-printer-review-no-behavior-change
owner: Sandboxie/core/dll/gdi.c
spec: docs/plan/srev-287-gdi-splwow64-printer-dc-retry-owner.md
schema: docs/plan/srev-287-gdi-splwow64-printer-dc-retry-owner.schema.json
checker: docs/plan/check-srev-287.py
runtime_gate: inherited from SREV-061 Windows 32-bit WINSPOOL CreateDCW retry after SplWow64 failure successful initial CreateDCW unchanged and no spooler path without lpszDevice
---

### SREV-287: GDI SplWow64 Printer DC Retry Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-061 and official SplWow64 printer review; no behavior change |
| Evidence | `Gdi_CreateDCW2` owns a 32-bit WINSPOOL `CreateDCW` retry path that runs only after the first native call fails and only when `lpszDriver` is `WINSPOOL`, `lpszDevice` is present, `DocumentPropertiesW` resolves, and retry count remains below 20. SREV-061 already corrected the source-level API shape so printer identity flows through `lpszDevice` while `lpInitData` remains DEVMODE input. The old function comment and `winspool.drv` loader registration comment described this as a generic workaround. |
| Data | `Gdi_CreateDCW2`, `Gdi_Init_Spool`, `winspool.drv`, `lpszDriver`, `lpszDevice`, `lpszOutput`, `lpInitData`, `WINSPOOL`, `SplWow64`, `OpenPrinter2W`, `DocumentPropertiesW`, `hPrinter`, retry delay, retry count, and native `CreateDCW` result. |
| Schema | `GDI_SPLWOW64_PRINTER_DC_RETRY_OWNER` says `Gdi_CreateDCW2` owns only the 32-bit WINSPOOL printer DC retry path; SREV-061 owns the `lpszDevice` printer-name and `lpInitData` DEVMODE separation; the `Gdi_CreateDCW2` source comment must name the SplWow64 printer-host bridge and SREV-061 gate rather than a generic workaround; the `winspool.drv` loader registration comment must name the SREV-287 32-bit WINSPOOL/SplWow64 printer DC retry owner; the retry remains bounded by WINSPOOL driver match, `lpszDevice` presence, `DocumentProperties` availability, and retry count; this SREV changes comments and proof only. |
| Topology | `32-bit process on 64-bit Windows -> WINSPOOL printer DC request -> SplWow64 print-driver host bridge -> Sandboxie Gdi_CreateDCW2 retry path -> printer-name wake/query edge -> same CreateDCW request`. |
| Logic Risk | Generic retry wording can hide the owner boundary and invite broadening the branch, removing the SREV-061 device-name gate, or treating `lpInitData` as printer identity again. |
| Official Shape | Microsoft documents `CreateDCW` printer device-name and DEVMODE inputs, `OpenPrinter2` printer-name opening, `DocumentProperties` printer handle/device-name behavior, and the 64-bit Windows Splwow64 bridge for 32-bit printing. |
| Fix | Comment-only source clarification. The source now names SREV-287, the 32-bit WINSPOOL to SplWow64 bridge, and the SREV-061 `lpszDevice` / `DocumentProperties` gate. The loader registration now names the same SREV-287 32-bit WINSPOOL/SplWow64 printer DC retry owner. No retry count, delay, native call, spooler call, or hook registration changed. |
| Acceptance Gate | `docs/plan/check-srev-287.py` validates the draft-07 schema, official references, source comment, loader registration comment, SREV-061 adjacency, unchanged `Gdi_CreateDCW2` retry behavior, stale workaround wording removal from the function and loader entry, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-287.sh` is the targeted wrapper. Runtime gate is inherited from SREV-061: Windows 32-bit WINSPOOL `CreateDCW` retry after SplWow64 failure, successful initial `CreateDCW` unchanged, and no spooler path when no printer device name is supplied. |
