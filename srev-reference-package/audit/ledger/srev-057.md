---
kind: srev-ledger-entry
id: SREV-057
title: Box Root DOS Path Publication Boundary
status: patched-source-level-after-official-unicode-string-wcscpy-nt-success-shape-plus-
owner: Sandboxie/core/dll/file_init.c
spec: docs/plan/srev-057-file-init-box-root-path.md
schema: docs/plan/srev-057-file-init-box-root-path.schema.json
checker: docs/plan/check-srev-057.py
runtime_gate: "normal box-root translation, reparse/no-drive raw-root fallback, direct allocation failure, raw-query failure, empty raw-root response, fallback allocation failure, over-`USHORT` byte capacity, and prefix consumers with zero-length gates"
---
### SREV-057: Box Root DOS Path Publication Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official UNICODE_STRING/wcscpy/NT_SUCCESS shape plus local `SbieApi_QueryProcessInfoStr` byte-capacity wire-shape analysis; needs Windows reparse/no-drive root runtime proof |
| Evidence | `Sandboxie/core/dll/file_init.c` initializes `Dll_BoxFileDosPath` from `Dll_BoxFilePath`, then falls back to `SbieApi_QueryProcessInfoStr(0, 'root', ...)` when the box root is redirected through a reparse point whose target device has no drive letter. Before this patch, both direct and fallback `Dll_BoxFileDosPath` allocations were used by `wcscpy` without allocation checks, and `Dll_BoxFileRawPath` was published before proving that the second raw-root query succeeded and returned a non-empty string. |
| Data | `Dll_BoxFilePath`, `Dll_BoxFilePathLen`, direct DOS-path allocation, raw-root byte length from `SbieApi_QueryProcessInfoStr`, raw-root temporary buffer, `Dll_BoxFileRawPath`, `Dll_BoxFileRawPathLen`, `Dll_BoxFileDosPath`, and `Dll_BoxFileDosPathLen`. |
| Schema | `FILE_INIT_BOX_ROOT_PATH_PUBLICATION` says global root path pointers may be published only after source string, allocation, query status, byte-capacity, and non-empty string gates succeed. Null global root pointers must keep zero length gates. |
| Topology | Box NT root flows first through direct NT-to-DOS translation. If that fails, the raw-root query fallback stages the raw path locally, then publishes raw and DOS globals only after validation. Later path consumers use pointer plus length as prefix gates. |
| Logic Risk | A root-path fallback is a global topology seed. Publishing a non-null raw pointer with a zero length, or copying into a failed allocation, can turn a compatibility fallback into crashes or empty-prefix path matches across later file routing. |
| Official Shape | `docs/plan/srev-057-file-init-box-root-path.md` records Microsoft `UNICODE_STRING`, `wcscpy`, and `NT_SUCCESS` references plus the local `SbieApi_QueryProcessInfoStr` `UNICODE_STRING64.MaximumLength` byte-capacity shape. `docs/plan/srev-057-file-init-box-root-path.schema.json` records the JSON Schema draft-07 local `FILE_INIT_BOX_ROOT_PATH_PUBLICATION` contract. |
| Fix | Direct DOS-path copy now runs only after allocation succeeds. The raw-root fallback now accepts only byte capacities that fit `UNICODE_STRING.MaximumLength`, queries into a local temporary buffer, publishes `Dll_BoxFileRawPath` only after allocation, query success, and non-empty string proof, checks fallback DOS-path allocation before `wcscpy`, and leaves globals null/zero-length on failed paths. |
| Acceptance Gate | `docs/plan/check-srev-057.py` validates the draft-07 schema, official references, local `SbieApi_QueryProcessInfoStr` shape, direct allocation gate, raw byte-capacity gate, local raw-path staging, raw query/non-empty gates before publication, fallback allocation gate, `File_AltBoxPath` legacy-fallback adjacency, SREV-264 adjacency, and ledger entry; `docs/plan/check-srev-057.sh` is the targeted wrapper. Windows gate: normal box-root translation, reparse/no-drive raw-root fallback, direct allocation failure, raw-query failure, empty raw-root response, fallback allocation failure, over-`USHORT` byte capacity, mount-point prefix matching, and prefix consumers with zero-length gates. |
