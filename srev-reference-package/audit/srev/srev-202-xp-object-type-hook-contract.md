# SREV-202: XP Object Type Hook Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/drv/obj_xp.c` was the top unnamed reviewable core file after
SREV-201. It is the Windows XP / Server 2003 object-type parse-procedure hook
owner. `File_Init_XpHook` and `Key_Init_XpHook` pass local constant type names
such as `File`, `Device`, and `Key` into `Obj_HookParseProc`, which opens
`\ObjectTypes\<TypeName>`, references the object, computes a private
`OBJECT_TYPE_INITIALIZER.ParseProcedure` offset, builds a hook entry, and
publishes it with `InterlockedExchangePointer`.

Before this fix, `Obj_HookAnyProc` built the object-type path with unchecked
`wcscpy` / `wcscat`, dereferenced `OldProc` and `pHookEntry` without an explicit
helper contract, accepted a null `NewProc`, and used `ProcOffset` without
proving it stayed inside the local `TypeInfo` projection before reading and
publishing the hook pointer.

## Data

`Obj_HookParseProc`, `Obj_HookAnyProc`, `Obj_BuildObjectTypeName`,
`TypeName`, `NewProc`, `OldProc`, `HookEntry`, `ProcOffset`,
`OBJECT_TYPE.TypeInfo`, `OBJECT_TYPE_INITIALIZER.ParseProcedure`,
`ObOpenObjectByName`, `ObReferenceObjectByHandle`,
`Process_BuildHookEntry`, `KeMemoryBarrier`, and
`InterlockedExchangePointer`.

## Official Shape

Microsoft documents `RtlInitUnicodeString` as initializing a
`UNICODE_STRING` from an optional source string, and
`InitializeObjectAttributes` as the macro that prepares `OBJECT_ATTRIBUTES`
for routines that open handles by object name.

Microsoft documents `ObReferenceObjectByHandle` as returning a pointer to the
object body and incrementing its reference count on success, with the caller
responsible for dereferencing the object. Microsoft also states that
system-defined objects can be opaque and that drivers should use documented
support routines instead of directly accessing opaque object internals.

`InterlockedExchangePointer` atomically exchanges the address stored at a target
pointer and has alignment requirements. That makes the hook publish edge a
pointer-sized write contract, not a byte-string contract.

This SREV does not make the private XP object-type structure an official API.
The private layout remains a local compatibility dependency. The patch only
adds owner-local gates before using that dependency.

References:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring`
- `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/nf-ntdef-initializeobjectattributes`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobjectbyhandle`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-based`
- `https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-interlockedexchangepointer`

## Schema

`XP_OBJECT_TYPE_HOOK_CONTRACT` says:

- The object-type path is built by the owner through a bounded helper.
- `TypeName`, `NewProc`, `OldProc`, and `pHookEntry` are required before any
  object open, reference, dereference, or hook publish path.
- `Obj_BuildObjectTypeName` rejects names that cannot fit in the local
  `WCHAR ObjectName[64]` buffer including the `\ObjectTypes\` prefix and null
  terminator.
- `ProcOffset` must point to a pointer-sized slot inside the local
  `OBJECT_TYPE.TypeInfo` projection before `OldProc` is read and before
  `InterlockedExchangePointer` publishes the hook entry.
- `Process_BuildHookEntry` success still gates hook publication.
- XP parse-procedure hook topology, private object-manager layout dependency,
  and File/Device/Key hook targets are unchanged.

## Topology

```text
File/Key XP init
-> Obj_HookParseProc(Type, NewFunc, OldFunc, HookEntry)
-> Obj_HookAnyProc input gate
-> bounded \ObjectTypes\<TypeName> path
-> ObOpenObjectByName
-> ObReferenceObjectByHandle
-> ProcOffset inside TypeInfo pointer slot
-> Process_BuildHookEntry
-> KeMemoryBarrier
-> InterlockedExchangePointer(TypeInfo.ParseProcedure, HookEntry)
```

## Logic Risk

The old source trusted helper callers to provide only small constant type names
and valid output pointers. Current callers do that, so this is not a proven
active overflow in the observed init path. The problem is that the helper's
actual owner boundary did not encode those assumptions. A future object type or
failed caller path could turn the unchecked path build or pointer output into a
kernel init crash or hook-publish corruption.

The private `OBJECT_TYPE` layout remains the larger architectural risk, but
that risk is not fixable from Microsoft public API shape without replacing the
XP hook strategy. This entry therefore gates only the deterministic local
inputs and offset math.

## Fix

`obj_xp.c` now:

- rejects null `TypeName`, null `NewProc`, null `OldProc`, and null
  `pHookEntry` before opening an object;
- builds `\ObjectTypes\<TypeName>` through `Obj_BuildObjectTypeName` with a
  fixed buffer-size gate;
- rejects `ProcOffset` values that cannot address a complete `ULONG_PTR`
  inside `object->TypeInfo`;
- preserves successful `Process_BuildHookEntry`, memory-barrier, and
  `InterlockedExchangePointer` topology.

## Acceptance Gate

`docs/plan/check-srev-202.py` validates the draft-07 schema, official
references, source-level input gates, bounded path builder, stale unchecked
`wcscpy` / `wcscat` removal, offset gate before hook pointer read/publish, and
split ledger fragment. Runtime/build gate: Windows XP / Server 2003 compatible
driver build or historical target build plus File, Device, and Key
parse-procedure hook initialization smoke.
