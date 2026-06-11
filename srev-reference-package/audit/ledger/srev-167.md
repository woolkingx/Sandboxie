---
kind: srev-ledger-entry
id: SREV-167
title: XP Key Hotfix Kernel Handle
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/drv/key_xp.c
spec: docs/plan/srev-167-xp-key-hotfix-kernel-handle.md
schema: docs/plan/srev-167-xp-key-hotfix-kernel-handle.schema.json
checker: docs/plan/check-srev-167.py
runtime_gate: "Windows XP/2003 32-bit XP_SUPPORT driver build, registry hotfix probe, catalog fallback probe, no-hotfix path, parse-procedure hook smoke, and unload smoke"
---

### SREV-167: XP Key Hotfix Kernel Handle

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft driver object-handle and `ZwOpenKey` documentation review; needs Windows XP/2003 runtime proof |
| Evidence | `Sandboxie/core/drv/key_xp.c` was the top unnamed reviewable core file after SREV-166. `Key_Check_KB979683` opens a registry key with `ZwOpenKey` and, if that fails, a catalog file with `ZwCreateFile` to detect the XP/2000 hotfix shape that changes registry parse context. The handle is used only inside the driver probe and closed with `ZwClose`, but before this SREV `InitializeObjectAttributes` used only `OBJ_CASE_INSENSITIVE`. |
| Data | `Sandboxie/core/drv/key_xp.c`, `Sandboxie/core/drv/key.c`, `Sandboxie/core/drv/obj.h`, `Key_Init_XpHook`, `Key_Check_KB979683`, `InitializeObjectAttributes`, `OBJECT_ATTRIBUTES`, `OBJ_CASE_INSENSITIVE`, `OBJ_KERNEL_HANDLE`, `ZwOpenKey`, `ZwCreateFile`, `ZwClose`, and `Key_Have_KB979683`. |
| Schema | `XP_KEY_HOTFIX_KERNEL_HANDLE` says `key_xp.c` owns the legacy XP key parse-procedure hook and hotfix probe; `Key_Check_KB979683` opens registry-key and catalog-file handles only for driver-private hotfix detection; driver-private handles opened through `ZwOpenKey` or `ZwCreateFile` must use object attributes with `OBJ_KERNEL_HANDLE`; the path remains case-insensitive; and successful probe handles remain closed by `ZwClose`. |
| Topology | Legal flow is `Key_Init_XpHook` -> `Key_Check_KB979683(KB...)` -> `InitializeObjectAttributes(OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE)` -> `ZwOpenKey` registry probe -> optional `ZwCreateFile` catalog probe -> `ZwClose` private handle -> `Key_Have_KB979683`. |
| Logic Risk | Without `OBJ_KERNEL_HANDLE`, a kernel-created handle can be placed in a process handle table when the driver is not running in the system process context. That is the wrong boundary for a private driver probe and can expose or confuse a handle that should be inaccessible to user mode. |
| Official Shape | `docs/plan/srev-167-xp-key-hotfix-kernel-handle.md` records Microsoft driver object-handle, `InitializeObjectAttributes`, and `ZwOpenKey` references. `docs/plan/srev-167-xp-key-hotfix-kernel-handle.schema.json` records the JSON Schema draft-07 local `XP_KEY_HOTFIX_KERNEL_HANDLE` contract. |
| Fix | `Key_Check_KB979683` now initializes `objattrs` with `OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE`. The same `OBJECT_ATTRIBUTES` object is used by the registry-key probe and the catalog-file fallback, so both opened handles inherit the kernel-handle attribute. Parse-procedure hook installation, `Key_Have_KB979683` detection logic, KB fallback list, ZoneAlarm wait hook behavior, and key access policy are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-167.py` validates the draft-07 schema, official references, XP include/dispatch topology, parse-procedure macro shape, `OBJ_KERNEL_HANDLE` in the hotfix probe object attributes, `ZwOpenKey` / `ZwCreateFile` / `ZwClose` preservation, stale non-kernel attribute rejection, and ledger entry; `docs/plan/check-srev-167.sh` is the matrix wrapper. Runtime/build gate: Windows XP/2003 32-bit driver build with `XP_SUPPORT`; KB979683-present registry probe; registry-missing catalog-file fallback probe; no-hotfix path; key parse-procedure hook smoke for `NtOpenKey` and `NtCreateKey`; unload smoke for hook disable. |
