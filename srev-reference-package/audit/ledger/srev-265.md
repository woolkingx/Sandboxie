---
kind: srev-ledger-entry
id: SREV-265
title: File AltBoxPath Allocation Publication Gate
status: patched-source-level-after-srev-196-tls-buffer-and-srev-264-prefix-owner-review-needs-windows-runtime
owner: Sandboxie/core/dll/file_init.c
spec: docs/plan/srev-265-file-altboxpath-allocation-publication-gate.md
schema: docs/plan/srev-265-file-altboxpath-allocation-publication-gate.schema.json
checker: docs/plan/check-srev-265.py
runtime_gate: Windows mount-point alternate box path smoke plus allocation failure injection for Dll_GetTlsNameBuffer and Dll_Alloc
---

### SREV-265: File AltBoxPath Allocation Publication Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after SREV-196 TLS buffer and SREV-264 prefix owner review; needs Windows runtime proof |
| Evidence | The mount-point alternate box path block allocates a TLS true-path buffer with `Dll_GetTlsNameBuffer`, copies `Dll_BoxFilePath` into it, converts mount-point links, allocates `File_AltBoxPath`, copies the converted path, and publishes `File_AltBoxPathLen`. Before this SREV, the first `wmemcpy` ran before checking whether `Dll_GetTlsNameBuffer` returned a non-null pointer. The second allocation was assigned directly to the global `File_AltBoxPath` before proving allocation success or initialization. SREV-196 already proves `Dll_GetTlsNameBuffer` can return null on allocation failure and must not publish failed allocations. |
| Data | `Dll_GetTlsNameBuffer`, `TruePath`, `Dll_BoxFilePath`, `Dll_BoxFilePathLen`, `File_GetName_ConvertLinks`, `Dll_Alloc`, `AltBoxPath`, `File_AltBoxPath`, and `File_AltBoxPathLen`. |
| Schema | `FILE_ALTBOXPATH_ALLOCATION_PUBLICATION_GATE` says `Dll_GetTlsNameBuffer` output must be checked before `wmemcpy` writes into it; the alternate mount-point path must be copied into a local allocation before `File_AltBoxPath` is published; `File_AltBoxPathLen` is published only after the pointer is non-null and initialized; this SREV does not change mount-point conversion semantics, prefix order, raw-root fallback semantics, or file policy. |
| Topology | `Dll_BoxFilePath -> Dll_GetTlsNameBuffer -> TruePath non-null gate -> wmemcpy + File_GetName_ConvertLinks -> Dll_Alloc local AltBoxPath -> copy initialized path -> publish File_AltBoxPath + File_AltBoxPathLen`. |
| Logic Risk | The old order could turn memory pressure into a null write in process initialization. It could also publish the global alternate prefix pointer before initialization, making later prefix consumers depend on a partially constructed fallback. |
| Official Shape | Microsoft documents `TlsGetValue` and `TlsSetValue` as TLS publication surfaces; SREV-196 records the local TLS/name-buffer allocation failure shape. Microsoft documents `wmemcpy` as copying a caller-provided element count from source to destination, which requires a valid destination buffer. |
| Fix | The first `wmemcpy` now runs only inside the `TruePath` non-null gate. The alternate path allocation is staged in a local `AltBoxPath` pointer, copied, and only then published to `File_AltBoxPath` with `File_AltBoxPathLen`. |
| Acceptance Gate | `docs/plan/check-srev-265.py` validates the draft-07 schema, official references, `file_init.c` gate order, removal of stale pre-gate copy/global-publish shape, SREV-196/SREV-264 adjacency, and the ledger fragment; `docs/plan/check-srev-265.sh` is the targeted wrapper. Runtime gate: Windows mount-point alternate box path smoke plus allocation failure injection for `Dll_GetTlsNameBuffer` and `Dll_Alloc`. |
