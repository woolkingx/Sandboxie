---
kind: srev-ledger-entry
id: SREV-181
title: Box Name Fixed Buffer Boundary
status: patched-source-level-after-official-ntstrsafe-copy-review-needs-windows-driver-runtime-proof
owner: Sandboxie/core/drv/box.c
spec: docs/plan/srev-181-box-name-fixed-buffer-boundary.md
schema: docs/plan/srev-181-box-name-fixed-buffer-boundary.schema.json
checker: docs/plan/check-srev-181.py
runtime_gate: "Windows driver build plus box creation smoke for valid names, invalid and oversized user-mode box-name rejection, invalid configuration section rejection for force-process discovery, and normal SID/session/file/key/ipc root creation for existing valid boxes"
---
### SREV-181: Box Name Fixed Buffer Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `ntstrsafe` bounded-copy review; needs Windows driver build/runtime proof |
| Evidence | `Sandboxie/core/drv/box.c` was the highest-ranked unnamed reviewable core file after SREV-180. `Sandboxie/core/drv/box.h` defines `BOX.name` as fixed `WCHAR name[BOXNAME_COUNT]` and documents sandbox identity as box name, user SID, and session. Before this SREV, `Box_Alloc` copied caller-supplied `boxname` into that fixed owner buffer with `wcscpy`, while validation lived in selected callers such as `Api_CopyBoxNameFromUser` rather than the owner write boundary. |
| Data | `Sandboxie/core/drv/box.c`, `Sandboxie/core/drv/box.h`, `Box_Alloc`, `Box_IsValidName`, `BOX.name`, `BOXNAME_COUNT`, `name_len`, `Box_Create`, `Box_CreateEx`, `Box_Clone`, `Api_CopyBoxNameFromUser`, `process_api.c`, `process_force.c`, `RtlStringCchCopyW`, `SID`, session id, and file/key/ipc root initialization. |
| Schema | `BOX_NAME_FIXED_BUFFER_BOUNDARY` says `box.c` owns writes into `BOX.name`; `BOX.name` has exactly `BOXNAME_COUNT` `WCHAR` slots; `Box_IsValidName` is the local semantic schema for box identity names; `Box_Alloc` rejects `NULL` or invalid box names before allocating owner state or writing `BOX.name`; `Box_Alloc` copies into `BOX.name` with a bounded API that receives `BOXNAME_COUNT`; copy failure frees the allocated `BOX` and fails closed; caller-side validation such as `Api_CopyBoxNameFromUser` is useful but is not the owner boundary; this SREV does not change valid box-name characters, enabled-box policy, SID/session ownership, path expansion, or process forcing. |
| Topology | Legal flow is `caller boxname` -> `Box_Alloc` owner boundary -> `Box_IsValidName` semantic gate -> allocate `BOX` -> `RtlStringCchCopyW(BOX.name, BOXNAME_COUNT, boxname)` -> derive `name_len` from copied owner buffer -> `Box_InitKeys` stores SID/session -> `Box_InitPaths` builds file/key/ipc roots. |
| Logic Risk | `BOX.name` is identity data, not only text. If `Box_Alloc` trusts all callers before a fixed-buffer `wcscpy`, the correctness of box identity depends on every current and future path preserving the same validation contract. That is the wrong owner topology: the fixed-buffer owner must enforce the name schema at the write boundary. |
| Official Shape | `docs/plan/srev-181-box-name-fixed-buffer-boundary.md` records Microsoft `RtlStringCchCopyW` and bounded string-length references. `docs/plan/srev-181-box-name-fixed-buffer-boundary.schema.json` records the JSON Schema draft-07 local `BOX_NAME_FIXED_BUFFER_BOUNDARY` contract. |
| Fix | `Box_Alloc` now rejects `NULL` or invalid names before allocation, logs `STATUS_INVALID_PARAMETER`, and copies into `BOX.name` with `RtlStringCchCopyW(box->name, BOXNAME_COUNT, boxname)`. If the bounded copy fails, it logs the status, frees the partial `BOX`, and returns `NULL`. No valid box-name character set, `Api_CopyBoxNameFromUser`, enabled-box policy, SID/session storage, path expansion, force-process discovery, or service broker wire shape changed. |
| Acceptance Gate | `docs/plan/check-srev-181.py` validates the draft-07 schema, official references, `BOX.name` fixed-buffer evidence, `Box_IsValidName` owner gate, bounded `RtlStringCchCopyW` copy with `BOXNAME_COUNT`, failure cleanup, removal of the direct `wcscpy(box->name, boxname)` write, representative caller evidence, and ledger fragment; `docs/plan/check-srev-181.sh` is the matrix wrapper. Runtime gate: Windows driver build plus box creation smoke for a valid box name, invalid/oversized user-mode box-name rejection through API paths, invalid configuration section rejection for force-process discovery, and normal SID, session, file/key/ipc root creation for existing valid boxes. |
