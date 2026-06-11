---
kind: srev-ledger-entry
id: SREV-048
title: IPC Query Symbolic Link Buffer
status: patched-source-level-after-official-zwopensymboliclinkobject-zwquerysymboliclink
owner: Sandboxie/core/drv/ipc.c
spec: docs/plan/srev-048-ipc-query-symbolic-link.md
schema: docs/plan/srev-048-ipc-query-symbolic-link.schema.json
checker: docs/plan/check-srev-048.py
runtime_gate: valid query, odd length, empty/unterminated input, read-only output mapping, exact-fit target, and too-small output buffer
---
### SREV-048: IPC Query Symbolic Link Buffer

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ZwOpenSymbolicLinkObject/ZwQuerySymbolicLinkObject and local shared-buffer shape analysis; needs Windows malformed-buffer proof |
| Evidence | The pre-patch `Ipc_Api_QuerySymbolicLink` in `Sandboxie/core/drv/ipc.c` divided `name_len` by `sizeof(WCHAR)` without rejecting odd byte counts, copied the entire shared user buffer into the kernel object-name buffer, and wrote output after `ProbeForRead` instead of `ProbeForWrite`. Local callers pass `name_len` as shared buffer capacity, not as the input object-name payload length. |
| Data | `API_QUERY_SYMBOLIC_LINK_ARGS` `name_buf` shared user buffer and `name_len` byte capacity. |
| Schema | `name_len` is an even non-empty byte capacity under the 4096-WCHAR cap. Input is a non-empty NUL-terminated symbolic-link object name inside that capacity. Output is the queried symbolic-link target plus a synthesized NUL written back into the same buffer only when it fits. |
| Topology | Sandboxed caller buffer crosses into driver object-manager symbolic-link query, then the result crosses back into the same caller buffer. |
| Logic Risk | Odd byte counts, unterminated input, full-capacity name copying, and read-probed output writeback make object identity and output safety depend on accidental buffer contents and exception behavior rather than a declared API contract. |
| Official Shape | `docs/plan/srev-048-ipc-query-symbolic-link.md` records Microsoft `ZwOpenSymbolicLinkObject` and `ZwQuerySymbolicLinkObject` references. `docs/plan/srev-048-ipc-query-symbolic-link.schema.json` records the JSON Schema draft-07 local `IPC_QUERY_SYMBOLIC_LINK_BUFFER` contract. |
| Fix | `Ipc_Api_QuerySymbolicLink` now rejects odd length, empty input, and unterminated input; copies only through the first input NUL into the kernel object name; keeps `ZwQuerySymbolicLinkObject` capacity as the shared buffer size; and writes output through `ProbeForWrite` only when target plus NUL fits. |
| Acceptance Gate | `docs/plan/check-srev-048.py` validates the draft-07 schema, byte-count alignment gate, bounded input terminator scan, removal of full-capacity name copying, `ProbeForWrite` output, and target-plus-NUL fit check; `docs/plan/check-srev-048.sh` is the matrix wrapper. Windows gate: valid query, odd length, empty/unterminated input, read-only output mapping, exact-fit target, and too-small output buffer. |
