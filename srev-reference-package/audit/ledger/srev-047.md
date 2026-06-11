---
kind: srev-ledger-entry
id: SREV-047
title: Key Low-Label Boxed Path
status: patched-source-level-after-official-zwopenkey-zwsetsecurityobject-and-local-boxe
owner: Sandboxie/core/drv/key.c
spec: docs/plan/srev-047-key-low-label-boxed-path.md
schema: docs/plan/srev-047-key-low-label-boxed-path.schema.json
checker: docs/plan/check-srev-047.py
runtime_gate: boxed key succeeds, out-of-box key is denied, odd/embedded-NUL input is invalid, and the intended boxed key receives the low label
---
### SREV-047: Key Low-Label Boxed Path

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official ZwOpenKey/ZwSetSecurityObject and local boxed-key topology analysis; needs Windows boxed-key low-label proof |
| Evidence | The pre-patch `Key_Api_SetLowLabel` comment in `Sandboxie/core/drv/key.c` said the path must be in the box, but the predicate used `Box_IsBoxedPath(proc->box, file, &objname)` and allowed the operation when that file-path predicate was false. The same path parser rounded odd byte counts down and accepted embedded NULs before converting the counted payload with `RtlInitUnicodeString`. |
| Data | `API_SET_LOW_LABEL_ARGS` `path_len` byte count and `path_str` registry-key path payload. |
| Schema | The path is a counted WCHAR registry-key path: even non-empty byte count, bounded by the local 512-WCHAR cap, copied into a kernel-owned NUL-terminated buffer, no embedded NULs. Low-label mutation is legal only when the path is inside the sandbox `key` root, not the `file` root. |
| Topology | Sandboxed caller asks the driver to open a registry key and apply `Driver_LowLabelSd`; the allowed edge is caller path -> boxed registry-key root -> `ZwOpenKey` -> `ZwSetSecurityObject`. |
| Logic Risk | Out-of-box registry-key paths could reach security descriptor mutation because the topology check used the wrong root and inverted the allow condition. |
| Official Shape | `docs/plan/srev-047-key-low-label-boxed-path.md` records Microsoft `ZwOpenKey` and `ZwSetSecurityObject` references. `docs/plan/srev-047-key-low-label-boxed-path.schema.json` records the JSON Schema draft-07 local `KEY_LOW_LABEL_BOXED_PATH` contract. |
| Fix | `Key_Api_SetLowLabel` now rejects odd length, allocation failure, and embedded NULs; checks `Box_IsBoxedPath(proc->box, key, &objname)`; and only then opens the key and applies the low-label security descriptor. |
| Acceptance Gate | `docs/plan/check-srev-047.py` validates the draft-07 schema, even-length and embedded-NUL gates, key-root boxed-path predicate, removal of the file-root/inverted predicate, and gating before `ZwOpenKey` / `ZwSetSecurityObject`; `docs/plan/check-srev-047.sh` is the matrix wrapper. Windows gate: boxed key succeeds, out-of-box key is denied, odd/embedded-NUL input is invalid, and the intended boxed key receives the low label. |
