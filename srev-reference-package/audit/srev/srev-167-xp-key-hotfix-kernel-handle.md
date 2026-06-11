# SREV-167: XP Key Hotfix Kernel Handle

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/drv/key_xp.c, Sandboxie/core/drv/key.c, Sandboxie/core/drv/obj.h, and Microsoft driver object-handle documentation
output artifact: XP registry hotfix probe opens driver-private key/file handles as kernel handles
owner: Sandboxie/core/drv/key_xp.c
acceptance gate: docs/plan/check-srev-167.py and docs/plan/check-srev-167.sh
```

## Data

`key_xp.c` owns the 32-bit Windows 2000/XP/2003 registry parse-procedure hook.
`Key_Check_KB979683` probes registry update keys and, if the registry key is
missing, a catalog file. It opens those objects with:

```c
ZwOpenKey(&handle, KEY_READ, &objattrs)
ZwCreateFile(&handle, FILE_GENERIC_READ, &objattrs, ...)
ZwClose(handle)
```

The handle is not returned to user mode, stored in process state, or shared with
any caller. It is a driver-private detection handle used only to decide
`Key_Have_KB979683`.

Before this SREV, `InitializeObjectAttributes` used only
`OBJ_CASE_INSENSITIVE`, so the handle was not explicitly marked
`OBJ_KERNEL_HANDLE`.

## Official Shape

- Microsoft driver object-handle documentation says whenever a driver creates
  an object handle for its private use, the driver must specify
  `OBJ_KERNEL_HANDLE`:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-handles`.
- Microsoft `InitializeObjectAttributes` documentation says driver routines
  that run in a process context other than the system process must set
  `OBJ_KERNEL_HANDLE`:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/nf-ntdef-initializeobjectattributes`.
- Microsoft `ZwOpenKey` documentation says if the caller is not running in a
  system thread context, it must set `OBJ_KERNEL_HANDLE` when it calls
  `InitializeObjectAttributes`, and must close the handle with `ZwClose` when
  done:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey`.

## Schema

`XP_KEY_HOTFIX_KERNEL_HANDLE` says:

- `key_xp.c` owns the legacy XP key parse-procedure hook and its hotfix probe.
- `Key_Check_KB979683` opens registry-key and catalog-file handles only for
  driver-private hotfix detection.
- Driver-private handles opened through `ZwOpenKey` or `ZwCreateFile` must use
  object attributes with `OBJ_KERNEL_HANDLE`.
- The path remains case-insensitive.
- Successful key/file probe handles remain closed by `ZwClose`.
- Parse-procedure hook installation, `Key_Have_KB979683` detection logic,
  KB fallback list, ZoneAlarm wait hook behavior, and key access policy are
  unchanged.
- Linux source gates are not Windows XP/2003 runtime proof.

## Topology

Legal XP hotfix probe flow:

```text
Key_Init_XpHook
  -> Key_Check_KB979683(KB...)
  -> InitializeObjectAttributes(OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE)
  -> ZwOpenKey registry probe
  -> optional ZwCreateFile catalog probe
  -> ZwClose private handle
  -> Key_Have_KB979683
```

The object handle does not cross to user mode. The driver remains the only owner
of the handle from open/create through close.

## Logic Risk

Without `OBJ_KERNEL_HANDLE`, a kernel-created handle can be placed in a process
handle table when the driver is not running in the system process context. That
is the wrong boundary for a private driver probe and can expose or confuse a
handle that should be inaccessible to user mode. Even when the common init path
runs in a safe context, the local contract should state the private-handle owner
explicitly.

## Fix

`Key_Check_KB979683` now initializes `objattrs` with
`OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE`. The same `OBJECT_ATTRIBUTES` object
is used by the registry-key probe and the catalog-file fallback, so both opened
handles inherit the kernel-handle attribute.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-167.py
bash docs/plan/check-srev-167.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-167.py &&
bash docs/plan/check-srev-167.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows XP/2003 32-bit driver build with `XP_SUPPORT`;
KB979683-present registry probe; registry-missing catalog-file fallback probe;
no-hotfix path; key parse-procedure hook smoke for `NtOpenKey` and
`NtCreateKey`; unload smoke for hook disable.
