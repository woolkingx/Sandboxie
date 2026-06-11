---
kind: srev-ledger-entry
id: SREV-303
title: Key WOW64 Service Request Allocation Gate
status: patched-source-level-wow64-service-request-allocation-gate-needs-windows-runtime-proof
owner: Sandboxie/core/dll/key.c
spec: docs/plan/srev-303-key-wow64-service-request-allocation-gate.md
schema: docs/plan/srev-303-key-wow64-service-request-allocation-gate.schema.json
checker: docs/plan/check-srev-303.py
runtime_gate: Windows x64 registry smoke with KEY_WOW64_32KEY callers, shared-key no-op, and allocation-failure injection
---

### SREV-303: Key WOW64 Service Request Allocation Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level WOW64 service request allocation gate; needs Windows runtime proof |
| Evidence | `Key_FixNameWow64` routes a 64-bit process that requests `KEY_WOW64_32KEY` through `Key_FixNameWow64_2`, because a 64-bit caller has no WOW64 `NtOpenKey` thunk to rewrite the native call locally. The old source carried a `ToDo: ???` and disabled `NoSysCallHooks` block at that decision point. `Key_FixNameWow64_2` then allocated a `FILE_OPEN_WOW64_KEY_REQ` and immediately wrote the request header and key path without proving the allocation succeeded. |
| Data | `Key_FixNameWow64`, `Key_FixNameWow64_2`, `DesiredAccess`, `KEY_WOW64_32KEY`, `Dll_IsWow64`, `FILE_OPEN_WOW64_KEY_REQ`, `MSGID_FILE_OPEN_WOW64_KEY`, `KeyPath_len`, `SbieDll_CallServer`, `FileServer::OpenWow64Key`, `RegOpenKeyEx`, `Key_GetName`, and `Key_FixNameWow64_3`. |
| Schema | `KEY_WOW64_SERVICE_REQUEST_ALLOCATION_GATE` says `Key_FixNameWow64` owns the 64-bit caller `KEY_WOW64_32KEY` service-assisted route; `Key_FixNameWow64_2` must prove `FILE_OPEN_WOW64_KEY_REQ` allocation before writing the request; `filewire.h` owns the byte-counted key path wire shape; `FileServer::OpenWow64Key` owns the server-side `RegOpenKeyEx KEY_WOW64_32KEY` operation; this SREV does not change WOW64 flag semantics or duplicate `Wow6432Node` cleanup. |
| Topology | `64-bit caller KEY_WOW64_32KEY -> Key_FixNameWow64_2 -> Dll_AllocTemp(req_len) -> allocation gate -> FILE_OPEN_WOW64_KEY_REQ writes -> MSGID_FILE_OPEN_WOW64_KEY -> FileServer::OpenWow64Key -> RegOpenKeyEx KEY_WOW64_32KEY -> returned key path -> Key_GetName`. |
| Logic Risk | The stale `NoSysCallHooks` comment hid the real owner: this path is a registry-view topology bridge, not a syscall-hook policy switch. The unchecked request allocation could crash locally under memory pressure before SbieSvc could return a normal failure status. |
| Official Shape | Microsoft documents separate 32-bit and 64-bit logical registry views on WOW64, the registry redirector's `Wow6432Node` mapping as reserved implementation detail, and `KEY_WOW64_32KEY` / `KEY_WOW64_64KEY` as explicit alternate-view selectors. `KEY_WOW64_32KEY` is legal for a 64-bit application to access the 32-bit registry view. |
| Fix | The route comment now names SREV-303 and the service-assisted `KEY_WOW64_32KEY` owner. The stale `ToDo: ???` and disabled `NoSysCallHooks` block were removed. `Key_FixNameWow64_2` now returns `STATUS_INSUFFICIENT_RESOURCES` if `Dll_AllocTemp(req_len)` fails, before writing the wire request. No WOW64 flag semantics, `FILE_OPEN_WOW64_KEY_REQ` layout, service message id, call-server route, `Key_GetName` normalization, or duplicate `Wow6432Node` cleanup changed. |
| Acceptance Gate | `docs/plan/check-srev-303.py` validates the draft-07 schema, official references, source route comment, client-side allocation gate before request writes, wire request shape, server-side `RegOpenKeyEx(... KEY_WOW64_32KEY ...)` adjacency, stale TODO removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-303.sh` is the targeted wrapper. Runtime gate: Windows x64 registry smoke for 64-bit callers requesting `KEY_WOW64_32KEY`, shared-key no-op behavior, request-allocation failure injection returning `STATUS_INSUFFICIENT_RESOURCES`, and existing 32-bit WOW64 caller redirection behavior. |
