---
kind: srev-ledger-entry
id: SREV-078
title: SysInfo HideHostProcess List Capacity
status: patched-source-level-after-official-heapalloc-heaprealloc-heapfree-shape-and-loc
owner: Sandboxie/core/dll/sysinfo.c
spec: docs/plan/srev-078-sysinfo-hidehostprocess-list.md
schema: docs/plan/srev-078-sysinfo-hidehostprocess-list.schema.json
checker: docs/plan/check-srev-078.py
runtime_gate: "`HideHostProcess` with 0 entries, a small list, more than 100 entries, and simulated allocation/reallocation failure keeps initialized list entries valid and does not silently truncate due to a fixed local limit"
---
### SREV-078: SysInfo HideHostProcess List Capacity

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `HeapAlloc` / `HeapReAlloc` / `HeapFree` shape and local `HideHostProcess` multi-string analysis; needs Windows process-list filtering runtime proof |
| Evidence | `Sandboxie/core/dll/sysinfo.c` `SysInfo_DiscardProcesses` builds a heap-owned multi-string list from repeated `HideHostProcess` settings, then scans it while filtering `SYSTEM_PROCESS_INFORMATION` records. Microsoft documents `HeapAlloc` as returning NULL on failure without exception flags, `HeapReAlloc` as preserving the original block when reallocation fails, and `HeapFree` as freeing `HeapAlloc` / `HeapReAlloc` memory. Before this patch, the list used a fixed `100 * 110` WCHAR capacity with the comment "should be enough" and logged a generic `HideProcess` message when full, so configured entries beyond the local guess were not imported into the filter list. |
| Data | Indexed `HideHostProcess` config values, per-entry temporary name buffer, heap-owned WCHAR multi-string, used character count, allocated character capacity, process image-name comparison loop, and final `HeapFree`. |
| Schema | `SYSINFO_HIDEHOSTPROCESS_LIST_CAPACITY` says the hidden-process list is a double-NUL-terminated WCHAR multi-string whose capacity grows to fit configured entries; the code must prove `used + entry + final terminator` before copying; `HeapReAlloc` failure preserves the old initialized list and stops importing new entries. |
| Topology | Config entries flow through `SbieApi_QueryConfAsIs` into a transient heap multi-string owned by `SysInfo_DiscardProcesses`; the process filtering loop consumes only initialized entries until the final terminator; the same owner frees the list after filtering. |
| Logic Risk | A process-hide policy should not depend on an arbitrary fixed local capacity. The old list topology made policy completeness depend on "100 processes should be enough" rather than the actual configured data shape, and its generic log did not preserve later entries for the current filtering pass. |
| Official Shape | `docs/plan/srev-078-sysinfo-hidehostprocess-list.md` records Microsoft `HeapAlloc`, `HeapReAlloc`, and `HeapFree` references. `docs/plan/srev-078-sysinfo-hidehostprocess-list.schema.json` records the JSON Schema draft-07 local `SYSINFO_HIDEHOSTPROCESS_LIST_CAPACITY` contract. |
| Fix | The fixed-size buffer is now a growable heap multi-string. The code tracks used length and capacity, grows with `HeapReAlloc` / `HeapAlloc` before copying a new entry, guards `ULONG` length addition/doubling, preserves the original list on reallocation failure, and keeps the final list terminator after every copied entry. |
| Acceptance Gate | `docs/plan/check-srev-078.py` validates the draft-07 schema, official references, dynamic capacity fields, overflow guard, grow-before-copy topology, `HeapReAlloc` / `HeapAlloc` use, stale fixed-capacity/log path removal, unchanged consumer iteration, and final free; `docs/plan/check-srev-078.sh` is the matrix wrapper. Windows gate: `HideHostProcess` with 0 entries, a small list, more than 100 entries, and simulated allocation/reallocation failure keeps initialized list entries valid and does not silently truncate due to a fixed local limit. |
