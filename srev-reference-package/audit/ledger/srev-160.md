---
kind: srev-ledger-entry
id: SREV-160
title: Obj Object Type Table Bound
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/drv/obj.c
spec: docs/plan/srev-160-obj-object-type-table-bound.md
schema: docs/plan/srev-160-obj-object-type-table-bound.schema.json
checker: docs/plan/check-srev-160.py
runtime_gate: "Windows WDK driver build, boot/load smoke, object type recognition smoke, and session monitor IPC object-existence smoke"
---

### SREV-160: Obj Object Type Table Bound

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after Object Manager and local table-schema review; needs Windows WDK build and session monitor runtime proof |
| Evidence | `Sandboxie/core/drv/obj.h` was the highest-ranked unnamed reviewable core file after SREV-159. It exposes `Obj_ObjectTypes` as a global `POBJECT_TYPE *` table. `Sandboxie/core/drv/obj.c` allocated ten pointer slots and zeroed them, then `Obj_AddObjectType` scanned with `for (i = 0; Obj_ObjectTypes[i]; ++i)` before writing `Obj_ObjectTypes[i]`. `Sandboxie/core/drv/session.c` consumes the same table as a NULL-terminated list while probing monitored IPC object existence. The current source inserts seven object types, so this was a latent table-schema defect rather than a present overflow. |
| Data | `Sandboxie/core/drv/obj.h`, `Sandboxie/core/drv/obj.c`, `Sandboxie/core/drv/session.c`, `Obj_ObjectTypes`, `Obj_Init`, `Obj_AddObjectType`, `ObReferenceObjectByName`, `STATUS_OBJECT_TYPE_MISMATCH`, object type pointers, and the NULL sentinel. |
| Schema | `OBJ_OBJECT_TYPE_TABLE_BOUND` says `Obj_ObjectTypes` is a fixed-capacity pointer table allocated by `Obj_Init`; the table is consumed as a NULL-terminated list by `session.c`; capacity includes one reserved sentinel slot; `Obj_AddObjectType` is the only writer and must prove an empty payload slot exists before writing a new `POBJECT_TYPE`; after each successful write, the next slot remains `NULL`; if no payload slot remains, initialization fails closed with a logged status instead of overwriting the sentinel or adjacent pool memory; and this SREV does not change which object types Sandboxie recognizes, object manager private probing, `ObQueryNameString` name construction, parse-proc hooks, minifilter callbacks, or session monitor semantics. |
| Topology | Legal construction is `Obj_Init` allocating `OBJ_OBJECT_TYPES_CAPACITY` pointer slots, zeroing all slots, calling `Obj_AddObjectType`, scanning only `[0, OBJ_OBJECT_TYPES_MAX)`, writing one payload slot, and keeping `i + 1` as the `NULL` sentinel. Legal consumption remains `session.c` iterating until `NULL`, calling `ObReferenceObjectByName`, and stopping when the status is no longer `STATUS_OBJECT_TYPE_MISMATCH`. |
| Logic Risk | The table pointer crosses an owner boundary: `obj.c` owns construction but `session.c` owns the consumer loop. Without an explicit writer bound, future object-type additions could overwrite the sentinel and let the consumer walk out of the allocation. This is not a Windows API behavior change; it is a local schema repair for a core object-manager table. |
| Official Shape | `docs/plan/srev-160-obj-object-type-table-bound.md` records Microsoft object-name, `ObReferenceObjectByHandle`, `MmGetSystemRoutineAddress`, and `ObQueryNameString` references. `docs/plan/srev-160-obj-object-type-table-bound.schema.json` records the JSON Schema draft-07 local `OBJ_OBJECT_TYPE_TABLE_BOUND` contract. |
| Fix | `obj.c` now names the table shape with `OBJ_OBJECT_TYPES_CAPACITY` and `OBJ_OBJECT_TYPES_MAX`. `Obj_Init` allocates and clears using the named capacity. `Obj_AddObjectType` scans only payload slots, fails closed with `STATUS_BUFFER_OVERFLOW` if no payload slot remains, writes the new object type, and refreshes the following sentinel slot to `NULL`. |
| Acceptance Gate | `docs/plan/check-srev-160.py` validates the draft-07 schema, official references, `obj.h` exported table, `obj.c` named capacity, capacity-based allocation/zeroing, bounded `Obj_AddObjectType` scan before write, sentinel refresh after write, stale unbounded writer loop removal, unchanged `session.c` NULL-sentinel consumer posture, and ledger entry; `docs/plan/check-srev-160.sh` is the matrix wrapper. Runtime/build gate: Windows WDK driver build, boot/load smoke proving `Obj_Init` still recognizes Job, Event, Mutant, Semaphore, Section, ALPC Port or Port, and SymbolicLink, plus session monitor IPC object-existence smoke. |
