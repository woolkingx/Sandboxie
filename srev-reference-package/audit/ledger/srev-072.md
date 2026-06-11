---
kind: srev-ledger-entry
id: SREV-072
title: File Recovery MUP Path Buffer
status: patched-source-level-after-official-wmemcpy-destination-buffer-shape-and-local-r
owner: Sandboxie/core/dll/file_recovery.c
spec: docs/plan/srev-072-file-recovery-mup-path-buffer.md
schema: docs/plan/srev-072-file-recovery-mup-path-buffer.schema.json
checker: docs/plan/check-srev-072.py
runtime_gate: recoverable LanmanRedirector/DFS/HGFS/MUP paths normalize when allocation succeeds; low-memory allocation failure avoids null write and falls back to original-path comparison
---
### SREV-072: File Recovery MUP Path Buffer

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `wmemcpy` destination-buffer shape and local recoverable-path normalization analysis; needs Windows network redirector recovery runtime proof |
| Evidence | `Sandboxie/core/dll/file_recovery.c` `File_IsRecoverable` translates LanmanRedirector/DFS/HGFS/MUP redirector paths into `\Device\Mup\...` form before comparing recover folders. Microsoft documents `wmemcpy` as copying into destination buffers. Before this patch, the redirector normalization branch called `Dll_Alloc(len2)` and immediately copied the MUP prefix and share suffix into `path2` without checking allocation success. |
| Data | Incoming `TruePath`, redirector prefix, share suffix after the prefix, allocated `path2`, MUP-normalized comparison path, recover-folder list comparison, and original-path fallback. |
| Schema | `FILE_RECOVERY_MUP_PATH_BUFFER` says `path2` is a legal wide-copy destination only after allocation succeeds; `TruePath` may be replaced by `path2` only after both prefix and suffix copies initialize the buffer. Allocation failure keeps the original `TruePath` and skips only local normalization. |
| Topology | Incoming file path flows through optional redirector normalization into the recover-folder comparison. `File_IsRecoverable` owns the temporary normalized buffer and must prove it before writes. |
| Logic Risk | Recovery classification should not crash on low memory while handling a network redirector path. The MUP translation is a local compatibility projection; if its buffer cannot be allocated, the function should continue with the original path rather than writing through null. |
| Official Shape | `docs/plan/srev-072-file-recovery-mup-path-buffer.md` records Microsoft `wmemcpy` references. `docs/plan/srev-072-file-recovery-mup-path-buffer.schema.json` records the JSON Schema draft-07 local `FILE_RECOVERY_MUP_PATH_BUFFER` contract. |
| Fix | `File_IsRecoverable` now checks `path2` before copying `File_Mup`, copying the redirector suffix, and assigning `TruePath = path2`. Allocation failure leaves `TruePath` unchanged. |
| Acceptance Gate | `docs/plan/check-srev-072.py` validates the draft-07 schema, official reference, allocation gate before prefix copy, suffix copy inside the gate, `TruePath` reassignment after initialization, stale ungated copy removal, and ledger entry; `docs/plan/check-srev-072.sh` is the matrix wrapper. Windows gate: recoverable LanmanRedirector/DFS/HGFS/MUP paths normalize when allocation succeeds; low-memory allocation failure avoids null write and falls back to original-path comparison. |
