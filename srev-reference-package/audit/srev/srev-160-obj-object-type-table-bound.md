# SREV-160: Obj Object Type Table Bound

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/drv/obj.h, Sandboxie/core/drv/obj.c, and Sandboxie/core/drv/session.c
output artifact: bounded NULL-terminated object-type table writer contract
owner: Sandboxie/core/drv/obj.c
acceptance gate: docs/plan/check-srev-160.py and docs/plan/check-srev-160.sh
```

## Data

`obj.h` exposes `Obj_ObjectTypes` as a global `POBJECT_TYPE *` table.
`obj.c` allocates that table during `Obj_Init`, populates it through
`Obj_AddObjectType`, and `session.c` later treats it as a NULL-terminated list
when probing whether a monitored IPC object exists.

Before this SREV, `Obj_Init` allocated ten pointer slots and zeroed them, but
the table capacity existed only as a literal. `Obj_AddObjectType` advanced with
`for (i = 0; Obj_ObjectTypes[i]; ++i)` and then wrote `Obj_ObjectTypes[i]`
without proving that `i` was still inside the capacity reserved for payload
entries plus the sentinel. The current set has seven inserted object types, so
this was not an immediate overflow in today's source. The defect is that the
writer contract did not encode the table schema it relied on.

## Official Shape

- Microsoft documents kernel object names as Unicode strings in an object
  namespace, and named objects are opened through object-manager names:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-names`.
- Microsoft documents `ObReferenceObjectByHandle` as validating the optional
  `ObjectType` parameter against the handle's object type and returning
  `STATUS_OBJECT_TYPE_MISMATCH` when it does not match:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobjectbyhandle`.
- Microsoft documents `MmGetSystemRoutineAddress` as a version-gated resolver
  for exported kernel/HAL routines, returning `NULL` when the name cannot be
  resolved:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-mmgetsystemroutineaddress`.
- Microsoft documents `ObQueryNameString` as returning an
  `OBJECT_NAME_INFORMATION` with a counted `UNICODE_STRING` name and
  `ReturnLength` as the byte size needed for the result:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-obquerynamestring`.

## Schema

`OBJ_OBJECT_TYPE_TABLE_BOUND` says:

- `Obj_ObjectTypes` is a fixed-capacity pointer table allocated by `Obj_Init`.
- the table is consumed as a NULL-terminated list by `session.c`.
- capacity includes one reserved sentinel slot.
- `Obj_AddObjectType` is the only writer and must prove an empty payload slot
  exists before writing a new `POBJECT_TYPE`.
- after each successful write, the next slot remains `NULL`.
- if no payload slot remains, initialization fails closed with a logged status
  instead of overwriting the sentinel or adjacent pool memory.
- this SREV does not change which object types Sandboxie recognizes, object
  manager private probing, `ObQueryNameString` name construction, parse-proc
  hooks, minifilter callbacks, or session monitor semantics.

## Topology

Legal construction flow:

```text
Obj_Init
-> allocate OBJ_OBJECT_TYPES_CAPACITY pointer slots
-> zero all slots
-> Obj_AddObjectType for each recognized type
-> scan only slots [0, OBJ_OBJECT_TYPES_MAX)
-> write payload slot
-> keep slot i + 1 as NULL sentinel
```

Legal consumer flow:

```text
session.c
-> for each Obj_ObjectTypes[i] until NULL sentinel
-> ObReferenceObjectByName with that object type
-> stop when the object status is no longer STATUS_OBJECT_TYPE_MISMATCH
```

## Logic Risk

The table pointer is a cross-file schema boundary: `obj.c` owns construction,
while `session.c` consumes NULL termination as proof of list length. A future
object-type addition, duplicate insertion path, or OS-specific insertion could
fill all ten slots and turn the sentinel into a payload entry, letting the
consumer walk past the allocation. The correct repair is owner-local: make the
capacity named, reserve a sentinel slot, and reject overflow at the only writer.

## Fix

`obj.c` now names the table shape with `OBJ_OBJECT_TYPES_CAPACITY` and
`OBJ_OBJECT_TYPES_MAX`. `Obj_Init` allocates and clears using the named
capacity. `Obj_AddObjectType` scans only payload slots, fails closed with
`STATUS_BUFFER_OVERFLOW` if no payload slot remains, writes the new object type,
and refreshes the following sentinel slot to `NULL`.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-160.py
bash docs/plan/check-srev-160.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-160.py &&
bash docs/plan/check-srev-160.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows WDK driver build; boot/load smoke proving
`Obj_Init` still recognizes Job, Event, Mutant, Semaphore, Section, ALPC Port or
Port, and SymbolicLink; session monitor IPC object-existence check still stops
at the sentinel and handles `STATUS_OBJECT_TYPE_MISMATCH` as before.
