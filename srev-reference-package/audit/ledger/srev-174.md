---
kind: srev-ledger-entry
id: SREV-174
title: DLL Path List Pool Lifetime
status: patched-source-level-after-official-critical-section-shape-and-local-pool-list-lifetime-review-needs-windows-refresh-runtime-proof
owner: Sandboxie/core/dll/dllpath.c
spec: docs/plan/srev-174-dllpath-pool-lifetime.md
schema: docs/plan/srev-174-dllpath-pool-lifetime.schema.json
checker: docs/plan/check-srev-174.py
runtime_gate: "Windows DLL build and refresh-failure smoke proving the last successfully published file path lists remain usable after a failed rebuild"
---

### SREV-174: DLL Path List Pool Lifetime

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official critical-section shape and local pool/list lifetime review; needs Windows refresh runtime proof |
| Evidence | `Sandboxie/core/dll/dllpath.c` was the highest-ranked unnamed reviewable core file after SREV-173. It owns the DLL-side path policy cache through `PATH_LIST_ANCHOR`, `Dll_InitPathList`, `Dll_InitPathList3`, `SbieDll_MatchPath2`, and `Dll_RefreshPathList`. `pool2` owns refreshable file-path `PATTERN` nodes. Before this SREV, `Dll_RefreshPathList` deleted the old `Dll_PathListAnchor->pool2` and assigned the replacement pool before `Dll_InitPathList2` proved the replacement lists were valid. A failed rebuild could therefore leave published list heads pointing into the freed old pool. `Dll_InitPathList` also leaked earlier pools when later initialization steps failed. |
| Data | `Sandboxie/core/dll/dllpath.c`, `Sandboxie/core/dll/sbieapi.c`, `Sandboxie/core/drv/process_api.c`, `Sandboxie/core/drv/file.c`, `Sandboxie/common/pool.c`, `PATH_LIST_ANCHOR`, `Dll_PathListAnchor`, `Dll_FilePathListCritSec`, `Dll_InitPathList`, `Dll_InitPathList2`, `Dll_InitPathList3`, `Dll_RefreshPathList`, `SbieApi_QueryPathList`, `API_REFRESH_FILE_PATH_LIST`, `Pool_Create`, `Pool_Delete`, `PATTERN`, and `LIST`. |
| Schema | `DLLPATH_POOL_LIFETIME` says `dllpath.c` owns the DLL-side path list cache and its pool/list lifetime; `pool2` owns refreshable file-path `PATTERN` nodes; refresh builds a complete replacement in a new pool before publishing it; refresh failure preserves the last successfully published file path lists and their pool; the old `pool2` may be deleted only after the replacement pool and list heads are published; partial replacements are discarded by deleting the replacement pool; `Dll_InitPathList` deletes earlier pools when later initialization fails; path code selection, pattern matching semantics, driver refresh ownership, lock ownership, and path-list wire format are unchanged. |
| Topology | `Dll_RefreshPathList` enters `Dll_FilePathListCritSec`, asks the driver to refresh file paths, creates a replacement `pool2`, builds temporary list heads in that pool, and publishes the pool and list heads only after `Dll_InitPathList2` succeeds. On success it deletes the old pool after publication; on failure it deletes the replacement pool and leaves the old pool/list pair intact. |
| Logic Risk | The list heads and their pool are one ownership unit. Deleting the old pool before the replacement list heads are valid breaks that unit. A failed refresh could make later path checks consume freed `PATTERN` memory or silently lose the read/write/closed policy that enforces the sandbox boundary. |
| Official Shape | `docs/plan/srev-174-dllpath-pool-lifetime.md` records Microsoft critical-section documentation as the shared-resource synchronization shape. This SREV introduces no new Windows API; it fixes local pool/list publication under the existing critical section. `docs/plan/srev-174-dllpath-pool-lifetime.schema.json` records the JSON Schema draft-07 local `DLLPATH_POOL_LIFETIME` contract. |
| Fix | `Dll_InitPathList` now deletes previously created pools when a later allocation fails. `Dll_RefreshPathList` now builds refreshed file path lists in a replacement pool, publishes the replacement pool and list heads only after the rebuild succeeds, deletes the old pool after publication, and deletes the replacement pool on rebuild failure. |
| Acceptance Gate | `docs/plan/check-srev-174.py` validates the draft-07 schema, official references, path-list API wrapper, driver wire producer, driver refresh owner, pool primitives, initialization cleanup, two-phase refresh publication, stale pre-build deletion rejection, and ledger fragment; `docs/plan/check-srev-174.sh` is the matrix wrapper. Runtime gate: Windows DLL build plus refresh-failure smoke proving initialized file path matching still uses the last successfully published rule set after a later rebuild fails. |
