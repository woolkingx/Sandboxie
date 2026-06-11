---
kind: srev-ledger-entry
id: SREV-216
title: PDH Status ABI Contract
status: patched-source-level-after-official-pdh-status-abi-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/pdh.c
declaration: Sandboxie/core/dll/dll.h
spec: docs/plan/srev-216-pdh-status-abi-contract.md
schema: docs/plan/srev-216-pdh-status-abi-contract.schema.json
checker: docs/plan/check-srev-216.py
runtime_gate: Windows DLL build plus sandboxed PDH smoke for PdhConnectMachineW and PdhLookupPerfNameByIndexW, proving callers receive a PDH failure status without successful performance-counter access and without unexpected output-buffer writes on denied calls.
---

### SREV-216: PDH Status ABI Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official PDH status ABI review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/dll/pdh.c` was the top unnamed reviewable core file after SREV-215. It owns Sandboxie's PDH deny hooks for `PdhConnectMachineW` and `PdhLookupPerfNameByIndexW`. Before this fix, both local function-pointer typedefs and both hook functions used `UINT`. The official PDH surface returns `PDH_STATUS`. The hook also returned `ERROR_ACCESS_DENIED`, a generic system error value, instead of the PDH-specific `PDH_ACCESS_DENIED` status that names the denied performance-data boundary. |
| Data | `pdh.c`, `dll.h`, `ldr.c`, `Pdh_Init`, `Pdh_PdhConnectMachineW`, `Pdh_PdhLookupPerfNameByIndexW`, `P_PdhConnectMachineW`, `P_PdhLookupPerfNameByIndexW`, `__sys_PdhConnectMachineW`, `__sys_PdhLookupPerfNameByIndexW`, `GetProcAddress`, `SBIEDLL_HOOK`, `PDH_STATUS`, `PDH_ACCESS_DENIED`, `PdhConnectMachineW`, and `PdhLookupPerfNameByIndexW`. |
| Schema | `PDH_STATUS_ABI_CONTRACT` says `pdh.c` owns Sandboxie's DLL-side PDH deny hooks; local PDH function-pointer typedefs use `PDH_STATUS`, matching the official PDH return contract; hook functions use `PDH_STATUS`, matching the resolved export ABI; policy denial returns `PDH_ACCESS_DENIED`; and hook installation plus the selected PDH export set remain unchanged. |
| Topology | Legal flow is `Pdh.dll export -> GetProcAddress -> local P_Pdh* typedef -> SBIEDLL_HOOK original-function storage -> Pdh_Pdh* replacement -> PDH_ACCESS_DENIED`. |
| Logic Risk | Hook wrappers are ABI boundaries. A generic integer return type hides the external API contract and makes future edits more likely to treat PDH as a plain Win32 `UINT` API. Returning generic `ERROR_ACCESS_DENIED` is allowed by some PDH documentation as a system error shape, but it does not name the performance-data policy denial that this module owns. The correct local schema is the official `PDH_STATUS` surface with explicit `PDH_ACCESS_DENIED`. |
| Official Shape | `docs/plan/srev-216-pdh-status-abi-contract.md` records Microsoft `PdhConnectMachineW`, `PdhLookupPerfNameByIndexW`, and PDH error-code references. `docs/plan/srev-216-pdh-status-abi-contract.schema.json` records the JSON Schema draft-07 local `PDH_STATUS_ABI_CONTRACT` contract. |
| Fix | `pdh.c` now includes `pdh.h`, declares the two PDH typedefs and hook functions with `PDH_STATUS`, and returns `PDH_ACCESS_DENIED` from both deny hooks. Hook selection, export resolution, and `SBIEDLL_HOOK` installation are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-216.py` validates the draft-07 schema, official references, `pdh.h` inclusion, `PDH_STATUS` typedef and hook signatures, `PDH_ACCESS_DENIED` policy return, unchanged `GetProcAddress`/`SBIEDLL_HOOK` topology, split ledger fragment, and removal of the stale `UINT`/generic `ERROR_ACCESS_DENIED` PDH return shape; `docs/plan/check-srev-216.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build plus sandboxed PDH smoke for `PdhConnectMachineW` and `PdhLookupPerfNameByIndexW`, proving callers receive a PDH failure status without successful performance-counter access and without unexpected output-buffer writes on denied calls. |
