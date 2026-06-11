---
kind: srev-ledger-entry
id: SREV-018
title: Dynamic RPC Port Re-Registration Leaves Existing Filter IDs Stale
status: patched-source-level-after-official-rpc-endpoint-map-and-local-policy-entry-anal
owner: "Sandboxie/core/drv/ipc_port.c:724-726"
spec: docs/plan/srev-018-dynamic-rpc-port-policy.md
schema: docs/plan/srev-018-dynamic-rpc-port-policy.schema.json
checker: docs/plan/check-srev-018.sh
runtime_gate: register id with filter A, re-register same id with filter B, verify only B applies
---
### SREV-018: Dynamic RPC Port Re-Registration Leaves Existing Filter IDs Stale

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official RPC endpoint-map and local policy-entry analysis; needs Windows runtime proof |
| Evidence | Explorer Hypatia reports `Sandboxie/core/drv/ipc_port.c:724-726` updates an existing dynamic port name but does not replace `FilterCount/FilterIDs`; new entries allocate filters at `ipc_port.c:735` and `ipc_port.c:746`; enforcement later uses the stale list at `ipc_port.c:845`. |
| Data | `IPC_DYNAMIC_PORT { portId, portName, FilterCount, FilterIDs[] }`. |
| Schema | A policy table entry is name plus filter list; if re-registration is legal, all policy fields must update atomically. |
| Topology | SbieSvc/EpMapper sends endpoint/filter policy to driver global dynamic-port table. |
| Logic Risk | Tightened config or changed endpoint deny list can leave old allow/deny policy active for a reused port id. |
| Official Shape | `docs/plan/srev-018-dynamic-rpc-port-policy.md` records Microsoft dynamic endpoint-map registration and replacement posture. |
| Fix | `Ipc_Api_OpenDynamicPort` now builds a full replacement `IPC_DYNAMIC_PORT` entry from the current port name and filter list, probes/copies filters before publication, atomically swaps same-id entries under the existing exclusive lock, updates the spooler cache pointer, and frees the old flexible-array entry. |
| Acceptance Gate | `docs/plan/check-srev-018.sh` proves re-registration no longer refreshes only the name and that filter payload is copied before publish. Windows gate: register id with filter A, re-register same id with filter B, verify only B applies. |
