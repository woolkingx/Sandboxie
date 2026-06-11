---
kind: srev-ledger-entry
id: SREV-037
title: IPC Create Directory Or Link Counted String
status: patched-source-level-after-official-unicode-string-rtlinitunicodestring-zwcreate
owner: "Sandboxie/core/drv/ipc.c:1634-1685"
spec: docs/plan/srev-037-ipc-create-dir-link-wire.md
schema: docs/plan/srev-037-ipc-create-dir-link-wire.schema.json
checker: docs/plan/check-srev-037.py
runtime_gate: normal create-directory/link plus odd-length, embedded-NUL, out-of-box target, and simulated tracking allocation failure preserve topology and handle ownership
---
### SREV-037: IPC Create Directory Or Link Counted String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official UNICODE_STRING/RtlInitUnicodeString/ZwCreateDirectoryObject symbolic-link shape analysis; needs Windows IPC object creation runtime proof |
| Evidence | `Sandboxie/core/drv/ipc.c:1634-1685` copied `objname` and optional `target` from user `UNICODE_STRING64` values using `user_len & ~1`, then passed local NUL-terminated buffers through `RtlInitUnicodeString` to `Box_IsBoxedPath` and object creation. `ipc.c:1739-1741` allocated `DIR_OBJ_HANDLE` after successful object creation and dereferenced it without checking allocation. |
| Data | `API_CREATE_DIR_OR_LINK_ARGS` carries required `objname` and optional `target`; absent `target` creates an object directory, present `target` creates a symbolic link. Successful object handles are persisted in `Ipc_ObjDirs`. |
| Schema | `UNICODE_STRING64.Length` is bytes, must be WCHAR-aligned, at least one WCHAR, below the local 2048-byte cap, and `<= MaximumLength`. Copied strings must not contain embedded NUL before `RtlInitUnicodeString`; successful handles must be either tracked in `Ipc_ObjDirs` or closed before return. |
| Topology | Sandboxed process API crosses into driver IPC object topology; `objname` and `target` are both checked against boxed IPC paths before `ZwCreateDirectoryObject` or `ZwCreateSymbolicLinkObject` can create host object-manager nodes. |
| Logic Risk | Odd byte lengths can silently truncate. Embedded NUL can make topology validation inspect a shorter path than the copied payload. Tracking allocation failure after object creation can dereference NULL and lose handle ownership. |
| Official Shape | `docs/plan/srev-037-ipc-create-dir-link-wire.md` records Microsoft `UNICODE_STRING`, `RtlInitUnicodeString`, `ZwCreateDirectoryObject`, and symbolic-link string references. `docs/plan/srev-037-ipc-create-dir-link-wire.schema.json` records the small local driver API schema. |
| Fix | `Ipc_Api_CreateDirOrLink` now copies both strings through `Ipc_Api_CreateDirOrLinkCopyString`, which rejects invalid counted byte shapes and embedded NULs. It also closes a newly created handle and returns `STATUS_INSUFFICIENT_RESOURCES` if `DIR_OBJ_HANDLE` tracking allocation fails. |
| Acceptance Gate | `docs/plan/check-srev-037.py` validates the schema, official references, counted-string helper, boxed topology checks, removal of `Length & ~1` in this API path, and handle cleanup on tracking allocation failure; `docs/plan/check-srev-037.sh` is the matrix wrapper. Windows gate: normal create-directory/link plus odd-length, embedded-NUL, out-of-box target, and simulated tracking allocation failure preserve topology and handle ownership. |
