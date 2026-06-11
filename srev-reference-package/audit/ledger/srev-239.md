---
kind: srev-ledger-entry
id: SREV-239
title: WFP Driver Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-driver-build-proof
owner: Sandboxie/core/drv/wfp.h
additional_owners:
  - Sandboxie/core/drv/wfp.c
  - Sandboxie/core/drv/driver.c
  - Sandboxie/core/drv/process.c
  - Sandboxie/core/drv/file.c
  - docs/plan/ledger/srev-027.md
spec: docs/plan/srev-239-wfp-driver-header-topology.md
schema: docs/plan/srev-239-wfp-driver-header-topology.schema.json
checker: docs/plan/check-srev-239.py
runtime_gate: Windows driver build continues to compile wfp.h and wire WFP module lifecycle through driver.c / process.c / file.c; runtime behavior remains covered by existing and future concrete-owner SREV Windows gates.
---

### SREV-239: WFP Driver Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows driver build proof |
| Evidence | `Sandboxie/core/drv/wfp.h` was the top unnamed reviewable core file after SREV-238. Source readback shows it is the declaration header for the driver Windows Filtering Platform module. It includes `driver.h` and exposes module lifecycle entry points plus process lifecycle entry points: `WFP_Init`, `WFP_Load`, `WFP_Unload`, `WFP_InitProcess`, `WFP_UpdateProcess`, and `WFP_DeleteProcess`. Runtime ownership lives in `wfp.c`, `driver.c`, `process.c`, and `file.c`. SREV-027 already owns the concrete WFP classify IRQL logging risk in `wfp.c`. |
| Data | `WFP_Init`, `WFP_Load`, `WFP_Unload`, `WFP_InitProcess`, `WFP_UpdateProcess`, `WFP_DeleteProcess`, `PROCESS`, `NetworkEnableWFP`, `WFP_Processes`, `WFP_MapLock`, `FwpmBfeStateSubscribeChanges`, `FwpmEngineOpen`, `FwpsCalloutRegister1`, `FwpmFilterAdd`, `WFP_classify`, `NetFwTrace`, `NetFw_BlockTraffic`, `driver.c`, `process.c`, and `file.c`. |
| Schema | `WFP_DRIVER_HEADER_TOPOLOGY_CONTRACT` says `wfp.h` is the driver WFP module declaration header; it may include `driver.h` and declare module lifecycle / process entry points that take or return local driver types; it does not own WFP engine sessions, BFE state callbacks, callout / sublayer / filter registration, classify IRQL behavior, network rule parsing, per-process rule maps, or settings refresh decisions; runtime behavior changes belong to `wfp.c`, `driver.c`, `process.c`, `file.c`, or NetFw rule owners depending on the transition; and future header changes must prove driver initialization, process lifecycle, settings refresh, and WFP callout topology before behavior claims. |
| Topology | `DriverEntry / driver initialization -> Driver_Init -> WFP_Init -> optional WFP_Load -> BFE state subscription -> WFP_Install_Callbacks -> WFP callout/sublayer/filter registration`; `process lifecycle -> Process_NotifyImage -> WFP_InitProcess -> WFP process map entry -> File_InitProcess / file setting refresh -> WFP_UpdateProcess -> WFP per-process network rules -> WFP_classify block/permit decision`; `process delete / driver unload -> WFP_DeleteProcess / WFP_Unload -> map cleanup and callout/filter engine close`. |
| Logic Risk | The high coverage score comes from `wfp.h` naming boundary-heavy entry points: kernel WFP callouts, driver initialization, network rule state, process lifecycle, and file/settings refresh coupling. Treating the header as the runtime owner would hide the real boundary and encourage edits in a file that cannot enforce WFP semantics. Behavior reviews must target the concrete owner that executes the crossing. |
| Official Shape | No new Windows/API runtime behavior is defined by this header. The official WFP classify IRQL, safe-string, spin-lock, ERESOURCE, pool, and data-logging references for the underlying callout behavior remain in SREV-027. This SREV is a local declaration/topology classification. |
| Fix | No source patch. This SREV records `wfp.h` as a declaration/topology header and closes it as docs-only coverage. Future behavior patches should target the owner that executes the relevant WFP engine, callout registration, classify, network-rule, process lifecycle, or settings refresh transition. |
| Acceptance Gate | `docs/plan/check-srev-239.py` validates the draft-07 schema, header declaration shape, `wfp.c` implementation topology, `driver.c` lifecycle callers, `process.c` lifecycle callers, `file.c` settings refresh callers, existing SREV-027 owner coverage, split ledger fragment, and absence of runtime owner code in this header; `docs/plan/check-srev-239.sh` is the targeted wrapper. Runtime/build gate: Windows driver build continues to compile `wfp.h` and wire WFP module lifecycle through `driver.c` / `process.c` / `file.c`; runtime behavior remains covered by existing and future concrete-owner SREV Windows gates. |
