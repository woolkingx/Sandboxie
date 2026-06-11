---
kind: srev-ledger-entry
id: SREV-043
title: Dynamic Port Fixed String
status: patched-source-level-after-official-probeforread-and-local-dynamic-port-shape-an
owner: "Sandboxie/core/drv/ipc_port.c:768-776"
spec: docs/plan/srev-043-dynamic-port-fixed-string.md
schema: docs/plan/srev-043-dynamic-port-fixed-string.schema.json
checker: docs/plan/check-srev-043.py
runtime_gate: dynamic port open/register with valid name, valid special id, empty name/id, and overlong unterminated name/id
---
### SREV-043: Dynamic Port Fixed String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ProbeForRead and local dynamic-port shape analysis; needs Windows dynamic port malformed-string proof |
| Evidence | `Sandboxie/core/drv/ipc_port.c:768-776` probed fixed dynamic port buffers and copied `DYNAMIC_PORT_NAME_CHARS - 1` / `DYNAMIC_PORT_ID_CHARS - 1` WCHARs into local buffers before appending NUL. Overlong unterminated user input could be silently truncated before dynamic IPC topology insertion or matching. |
| Data | Required dynamic `port_name`, optional `port_id`, and optional RPC filter IDs passed through `API_OPEN_DYNAMIC_PORT`. |
| Schema | Present dynamic port fixed strings are user pointers, readable under the existing fixed caps with WCHAR alignment, non-empty, and NUL-terminated before the final local terminator slot. Overlong unterminated input is invalid, not truncated. |
| Topology | `Ipc_Api_OpenDynamicPort` copies/proves user strings before `Ipc_CreateDynamicPort` stores special ports or `Process_AddPath` opens the dynamic IPC path for a process. |
| Logic Risk | Silent truncation can register or open a different dynamic IPC endpoint than the caller supplied, making later `_wcsicmp` matching and `Process_AddPath` operate on altered identity. |
| Official Shape | `docs/plan/srev-043-dynamic-port-fixed-string.md` records Microsoft `ProbeForRead` reference. `docs/plan/srev-043-dynamic-port-fixed-string.schema.json` records the small local dynamic-port schema. |
| Fix | `Ipc_Api_OpenDynamicPort` now routes `port_name` and present `port_id` through `Ipc_CopyFixedUserWString`, which rejects NULL, empty, and overlong unterminated input before local dynamic-port state is changed. |
| Acceptance Gate | `docs/plan/check-srev-043.py` validates the schema, helper shape, removal of truncating fixed-buffer copies, and helper routing for both `port_name` and `port_id`; `docs/plan/check-srev-043.sh` is the matrix wrapper. Windows gate: dynamic port open/register with valid name, valid special id, empty name/id, and overlong unterminated name/id. |
