---
kind: srev-ledger-entry
id: SREV-056
title: File Delete Path Tree Buffer Boundary
status: patched-source-level-after-microsoft-crt-wide-string-wmemmove-shape-and-local-fi
owner: Sandboxie/core/dll/file_del.c
spec: docs/plan/srev-056-file-del-path-tree-buffer.md
schema: docs/plan/srev-056-file-del-path-tree-buffer.schema.json
checker: docs/plan/check-srev-056.py
runtime_gate: normal path-tree save, fake nonexistent-drive save, deep-tree skip/no overrun, allocation failure, and malformed/empty translation input
---
### SREV-056: File Delete Path Tree Buffer Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft CRT wide-string/wmemmove shape and local file-delete path-tree serializer analysis; needs Windows deleted-file DAT tree proof |
| Evidence | `Sandboxie/core/dll/file_del.c` serializes a deleted-file path tree through a single `0x7FFF + 1` WCHAR buffer. The source has a `Hack Hack` comment for fake nonexistent-drive entries like `\C:\path`. Before this patch, `File_SavePathNode_internal` appended recursive slashes and child names without carrying capacity, `File_SavePathTree_internal` used the allocation result without checking it, and `File_TranslateNtToDosPathForDatFile` dereferenced its output allocation and searched from `DosPath + 1` without rejecting null or empty input. |
| Data | `PATH_NODE` component names, recursive full-path `WCHAR` buffer, `PathCapacity`, fake nonexistent-drive `\C:\...` paths, translated DOS path allocation, and DAT-file write path. |
| Schema | `FILE_DEL_PATH_TREE_BUFFER` says the serializer owns a fixed `0x7FFF + 1` WCHAR buffer; every slash and component append must fit with the terminating NUL; translation requires non-null non-empty input and a checked DOS-path allocation before wide-string operations. |
| Topology | The deleted-file path tree flows into the fixed serializer buffer, then through NT-to-DOS translation, then into the DAT-file writer. The serializer owns buffer bounds; the translator owns the returned allocated DOS path. |
| Logic Risk | A persistence-path workaround should not turn malformed/deep tree data or low memory into process memory corruption or null dereference. Without capacity propagation, recursive tree serialization can exceed the single temporary buffer. Without allocation/input gates, the fake-drive translation path can crash before it can preserve or skip the entry. |
| Official Shape | `docs/plan/srev-056-file-del-path-tree-buffer.md` records Microsoft CRT wide-character, `wcschr`, and `wmemmove` references. `docs/plan/srev-056-file-del-path-tree-buffer.schema.json` records the JSON Schema draft-07 local `FILE_DEL_PATH_TREE_BUFFER` contract. |
| Fix | `File_SavePathNode_internal` now carries `PathCapacity`, rejects slash append overflow, and skips child components that cannot fit with their NUL terminator. `File_SavePathTree_internal` checks path-buffer allocation and closes the output file on allocation failure. `File_TranslateNtToDosPathForDatFile` rejects null/empty input and checks DOS-path allocation before `wcscpy`, `wcschr`, or `wmemmove`. |
| Acceptance Gate | `docs/plan/check-srev-056.py` validates the draft-07 schema, official references, recursive capacity propagation, slash/component fit gates, allocation checks, null/empty translation input gate, and ledger entry; `docs/plan/check-srev-056.sh` is the matrix wrapper. Windows gate: normal path-tree save, fake nonexistent-drive save, deep-tree skip/no overrun, allocation failure, and malformed/empty translation input. |
