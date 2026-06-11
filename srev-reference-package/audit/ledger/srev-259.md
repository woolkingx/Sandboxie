---
kind: srev-ledger-entry
id: SREV-259
title: Custom Acscmonitor Loader Reference
status: patched-comment-topology-after-official-loader-reference-review-no-behavior-change
owner: Sandboxie/core/dll/custom.c
spec: docs/plan/srev-259-custom-acscmonitor-loader-reference.md
schema: docs/plan/srev-259-custom-acscmonitor-loader-reference.schema.json
checker: docs/plan/check-srev-259.py
runtime_gate: Windows Firefox plus ActivClient acscmonitor.dll compatibility smoke remains required before behavior changes
---

### SREV-259: Custom Acscmonitor Loader Reference

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official loader-reference review; no behavior change |
| Evidence | `Acscmonitor_LoadLibrary` creates an extra `LoadLibraryW(L"acscmonitor.dll")` reference from a helper thread. The old comment described only the Firefox crash symptom and said the library is prevented from ever being removed. It did not name the official loader reference-count boundary. |
| Data | `Acscmonitor_Init`, `CreateThread`, `Acscmonitor_LoadLibrary`, `LoadLibraryW`, `FreeLibrary`, `acscmonitor.dll`, module reference count, and late initialize / unload ordering. |
| Schema | `CUSTOM_ACSCMONITOR_LOADER_REFERENCE` says `Acscmonitor_LoadLibrary` owns the extra loader reference for `acscmonitor.dll`; the local behavior depends on the official `LoadLibraryW` / `FreeLibrary` per-process module reference-count model; `CreateThread` is only the deferral/execution edge for taking the reference; this SREV does not change the loaded DLL name, thread creation, handle close, module reference release policy, or Firefox/ActivClient compatibility behavior. |
| Topology | `Acscmonitor_Init -> CreateThread(Acscmonitor_LoadLibrary) -> LoadLibraryW("acscmonitor.dll") -> extra process-local module reference -> later FreeLibrary attempts do not unload while the extra reference remains`. |
| Logic Risk | Symptom-only crash wording hides the actual owner: this is a deliberate loader reference lifetime shim. Future changes must reason about module reference counts and unload ordering, not only Firefox plugin behavior. |
| Official Shape | `docs/plan/srev-259-custom-acscmonitor-loader-reference.md` records Microsoft `LoadLibraryW`, `FreeLibrary`, and `CreateThread` references. `docs/plan/srev-259-custom-acscmonitor-loader-reference.schema.json` records the JSON Schema draft-07 local `CUSTOM_ACSCMONITOR_LOADER_REFERENCE` contract. |
| Fix | Comment-only source clarification. The comments now describe the loader reference lifetime boundary and the late initialize / final unload race. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-259.py` validates the draft-07 schema, official reference links, source comments, removal of symptom-only crash wording, preservation of `CreateThread`, `CloseHandle`, and `LoadLibraryW` behavior, and the ledger fragment; `docs/plan/check-srev-259.sh` is the targeted wrapper. Runtime gate: Windows Firefox plus ActivClient `acscmonitor.dll` compatibility smoke remains required before changing behavior. |
