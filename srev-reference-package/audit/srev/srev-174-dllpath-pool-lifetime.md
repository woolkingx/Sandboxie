# SREV-174: DLL Path List Pool Lifetime

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/dllpath.c, SbieApi_QueryPathList, File_Api_RefreshPathList, Pool_Create/Pool_Delete, Microsoft critical section documentation
output artifact: DLL file path refresh publishes a newly built rule pool only after successful rebuild and preserves the last good rule set on refresh failure
owner: Sandboxie/core/dll/dllpath.c
acceptance gate: docs/plan/check-srev-174.py and docs/plan/check-srev-174.sh
```

## Data

`dllpath.c` owns the Sandboxie DLL-side path policy cache. The cache stores
file, key, and IPC path rules as `LIST` heads whose `PATTERN` nodes are allocated
from `PATH_LIST_ANCHOR` pools.

For file paths, `pool2` owns the refreshable rule set:

- `Dll_InitPathList` creates the anchor, `pool`, and `pool2`.
- `Dll_InitPathList3` calls `SbieApi_QueryPathList`, creates `PATTERN` nodes,
  and inserts them into temporary `LIST` heads.
- `Dll_RefreshPathList` asks the driver to refresh file path data, rebuilds the
  DLL-side list heads, and publishes them under `Dll_FilePathListCritSec`.

Before this SREV, `Dll_RefreshPathList` deleted `Dll_PathListAnchor->pool2` and
assigned the new pool before proving `Dll_InitPathList2` succeeded. If the new
list build failed, the old `LIST` heads still remained in the anchor while their
nodes had already been freed with the old pool.

`Dll_InitPathList` also leaked the first created pools when the second pool or
anchor allocation failed.

## Official Shape

- Microsoft documents critical section objects as process-local mutual exclusion
  for shared resources, entered with `EnterCriticalSection` and released with
  `LeaveCriticalSection`:
  `https://learn.microsoft.com/en-us/windows/win32/sync/critical-section-objects`.
- Microsoft documents `InitializeCriticalSectionAndSpinCount` and states that
  initialized critical sections are used with `EnterCriticalSection`,
  `TryEnterCriticalSection`, or `LeaveCriticalSection`, and should be deleted
  when no longer needed:
  `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-initializecriticalsectionandspincount`.

No new Windows API shape is introduced here. The Windows-facing boundary remains
the existing critical section around the DLL-side file path cache. The repaired
schema is local: path-list pool ownership must be swapped atomically with the
list heads it owns.

## Schema

`DLLPATH_POOL_LIFETIME` says:

- `dllpath.c` owns the DLL-side path list cache and its pool/list lifetime.
- `pool2` owns refreshable file path `PATTERN` nodes.
- File path refresh must build a complete replacement in a new pool before
  publishing it.
- Refresh failure must preserve the last successfully published file path lists
  and their pool.
- The old `pool2` may be deleted only after the new pool and list heads are
  published.
- Partially built replacement lists are discarded by deleting the replacement
  pool.
- `Dll_InitPathList` must delete earlier pools when later initialization steps
  fail.
- SREV-174 does not change path code selection, pattern matching semantics,
  driver refresh ownership, lock ownership, or the path list wire format.
- Linux source gates are not Windows refresh/runtime proof.

## Topology

Legal refresh topology after this SREV:

```text
Dll_RefreshPathList
  -> enter Dll_FilePathListCritSec
  -> API_REFRESH_FILE_PATH_LIST succeeds
  -> create replacement pool2
  -> build temporary LIST heads in replacement pool2
  -> if build succeeds:
       capture old pool2
       publish replacement pool2
       publish replacement LIST heads
       mark file paths initialized
       delete old pool2
     else:
       delete replacement pool2
       keep old pool2 and old LIST heads
  -> leave Dll_FilePathListCritSec
```

This preserves the user's policy intent: a sandbox can simplify to a few
semantic levels, but the runtime must never lose the last known-good rule map
while refreshing those levels.

## Logic Risk

The list heads and the pool are one ownership unit. Replacing the pool before
the new list heads are valid breaks that unit. A failed refresh can leave the
anchor pointing at freed `PATTERN` nodes, causing later path checks to consume
released memory or to silently lose the read/write/closed policy that makes the
sandbox boundary meaningful.

The correct minimal repair is a two-phase publish: construct the replacement in
private state, then swap the pool and list heads only after construction
succeeds.

## Action

`Dll_InitPathList` now deletes previously created pools when a later allocation
fails.

`Dll_RefreshPathList` now creates a replacement `pool2`, builds replacement
lists in that pool, publishes the pool and lists only after
`Dll_InitPathList2` succeeds, then deletes the old pool. If the rebuild fails,
the replacement pool is deleted and the previously published lists remain
intact.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-174.py
bash docs/plan/check-srev-174.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-174.py &&
bash docs/plan/check-srev-174.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows DLL build plus refresh-failure smoke proving an
already initialized file path cache remains usable when a later
`SbieApi_QueryPathList`/`Dll_InitPathList2` rebuild fails.
