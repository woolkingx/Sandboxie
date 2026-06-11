---
kind: srev-ledger-entry
id: SREV-176
title: Key Utility Registry Path Shape
status: patched-source-level-after-official-key-name-and-object-attributes-shape-review-needs-windows-dll-build-runtime-proof
owner: Sandboxie/core/dll/key_util.c
spec: docs/plan/srev-176-key-util-registry-path-shape.md
schema: docs/plan/srev-176-key-util-registry-path-shape.schema.json
checker: docs/plan/check-srev-176.py
runtime_gate: "Windows DLL build plus sandbox customization smoke for DCOM AppID Shell CLSID helpers root-relative registry opens and longer CLSID paths"
---

### SREV-176: Key Utility Registry Path Shape

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official key-name and object-attributes shape review; needs Windows DLL build/runtime proof |
| Evidence | `Sandboxie/core/dll/key_util.c` was the highest-ranked unnamed reviewable core file after SREV-175. `Key_OpenIfBoxed` manually queried `KEY_NAME_INFORMATION` with a fixed `PAGE_SIZE` buffer, appended `ObjectName->Buffer` with `wcscpy`, consumed the result as a NUL-terminated path, and did not free the allocation. `Key_DeleteValueFromCLSID` built a registry CLSID path in a fixed 128-WCHAR temporary buffer and did not free it. |
| Data | `Sandboxie/core/dll/key_util.c`, `Sandboxie/core/dll/key.c`, `Key_OpenIfBoxed`, `Key_OpenOrCreateIfBoxed`, `Key_DeleteValueFromCLSID`, `Key_GetName`, `OBJECT_ATTRIBUTES`, `UNICODE_STRING`, `KEY_NAME_INFORMATION`, `SbieDll_MatchPath`, `PATH_WRITE_FLAG`, and `STATUS_BAD_INITIAL_PC`. |
| Schema | `KEY_UTIL_REGISTRY_PATH_SHAPE` says `Key_GetName` owns key path normalization for `RootDirectory + UNICODE_STRING ObjectName`; `Key_OpenIfBoxed` must not create a second registry path builder from `KEY_NAME_INFORMATION`; it must match policy against the NUL-terminated true path returned by `Key_GetName`; `Key_OpenOrCreateIfBoxed` saves and restores `SecurityDescriptor` with the correct pointer level; `Key_DeleteValueFromCLSID` allocates from measured path length and frees the buffer before return. |
| Topology | Legal flow is `OBJECT_ATTRIBUTES -> Key_GetName -> NUL-terminated TruePath -> SbieDll_MatchPath('k') -> NtOpenKey or STATUS_BAD_INITIAL_PC`. The CLSID helper now flows `measured prefix/class/GUID path -> Key_OpenIfBoxed policy gate -> NtDeleteValueKey -> Dll_Free(path)`. |
| Logic Risk | Windows returns counted registry names and object names. Treating `KEY_NAME_INFORMATION.Name` or `UNICODE_STRING.Buffer` as NUL-terminated can over-read, and appending the relative name into a fixed `PAGE_SIZE` buffer can overwrite adjacent pool data. The fixed 128-WCHAR CLSID path had the same unchecked string-construction shape. Repeated calls leaked helper buffers. |
| Official Shape | `docs/plan/srev-176-key-util-registry-path-shape.md` records Microsoft `KEY_NAME_INFORMATION`, `ZwQueryKey`, and `OBJECT_ATTRIBUTES` shape. `docs/plan/srev-176-key-util-registry-path-shape.schema.json` records the JSON Schema draft-07 local `KEY_UTIL_REGISTRY_PATH_SHAPE` contract. |
| Fix | `Key_OpenIfBoxed` now calls `Key_GetName` and passes its true path to `SbieDll_MatchPath`; the manual `NtQueryKey`/`KEY_NAME_INFORMATION` path builder was removed. `Key_OpenOrCreateIfBoxed` saves `SecurityDescriptor` with the same pointer level it restores. `Key_DeleteValueFromCLSID` measures the prefix/class/GUID path, allocates exact storage, formats it with `Sbie_snwprintf`, and frees it. No registry policy model, custom app behavior, CLSID value names, WOW64 access flags, or create-on-missing behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-176.py` validates the draft-07 schema, official references, `Key_OpenIfBoxed` ownership transfer to `Key_GetName`, removal of the private `KEY_NAME_INFORMATION` builder, preservation of the `PATH_WRITE_FLAG`/`STATUS_BAD_INITIAL_PC` gate, correct `SecurityDescriptor` save type, measured CLSID path allocation, `Dll_Free(path)`, the isolation coordinate, and ledger fragment; `docs/plan/check-srev-176.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build plus sandbox customization smoke for DCOM/AppID/Shell CLSID helpers, root-relative registry opens, and longer CLSID paths. |
