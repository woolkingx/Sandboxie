---
kind: srev-ledger-entry
id: SREV-201
title: NetApi Slave Drive Command Contract
status: patched-source-level-after-official-netapi-definedosdevice-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/netapiserver.h
implementation: Sandboxie/core/svc/netapiserver.cpp
spec: docs/plan/srev-201-netapi-slave-drive-command-contract.md
schema: docs/plan/srev-201-netapi-slave-drive-command-contract.schema.json
checker: docs/plan/check-srev-201.py
runtime_gate: Windows service build plus valid mapped-drive broadcast and malformed NetProxy command smoke
---

### SREV-201: NetApi Slave Drive Command Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official NetAPI/DefineDosDevice shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/netapiserver.h` was the top unnamed reviewable core file after SREV-200. Its implementation launches `Sandboxie_NetProxy:Use=<drive>` after successful `NetUseAdd` and the slave calls `DefineDosDevice(DDD_LUID_BROADCAST_DRIVE, "<drive>:", NULL)`. Before this fix, `LaunchSlave` accepted any two-character local string ending in `:`, and `RunSlave` accepted the first character after `:Use=` without proving it was a drive letter or that the command ended after it. |
| Data | `NetApiServer::UseAdd`, `LaunchSlave`, `RunSlave`, `ui0_local`, `NetUseAdd`, `USE_INFO_2.ui2_local`, `CreateProcessAsUser`, `Sandboxie_NetProxy:Use=<drive>`, `DefineDosDevice`, and `DDD_LUID_BROADCAST_DRIVE`. |
| Schema | `NETAPI_SLAVE_DRIVE_COMMAND_CONTRACT` says only a single A-Z/a-z drive letter followed by `:` may launch the helper; only a valid drive-letter command with a terminator may reach `DefineDosDevice`; `DefineDosDevice` receives an uppercase `X:` device name; existing `NetUseAdd` policy and success-only `LaunchSlave` topology are preserved. |
| Topology | Legal flow is `NetUseAdd success -> LaunchSlave(len, local) drive-letter gate -> helper command -> WinMain NetProxy detection -> RunSlave command gate -> DefineDosDevice("X:", NULL)`. |
| Logic Risk | The old code treated the command text as a trusted internal string, but `RunSlave` is selected by a substring in the process command line. A malformed direct command or malformed local-device string could still enter the MS-DOS device namespace API with an invalid device name. |
| Official Shape | `docs/plan/srev-201-netapi-slave-drive-command-contract.md` records Microsoft `NetUseAdd`, `USE_INFO_2`, `DefineDosDeviceW`, and `CreateProcessAsUserW` references. `docs/plan/srev-201-netapi-slave-drive-command-contract.schema.json` records the JSON Schema draft-07 local `NETAPI_SLAVE_DRIVE_COMMAND_CONTRACT` contract. |
| Fix | `netapiserver.cpp` now has shared drive-letter and command-terminator helpers. `LaunchSlave` requires a two-character local device with an A-Z/a-z drive letter and `:`. `RunSlave` requires `:Use=`, a valid drive letter, and a command terminator before calling `DefineDosDevice`, and passes the normalized uppercase drive. |
| Acceptance Gate | `docs/plan/check-srev-201.py` validates the draft-07 schema, official references, header/implementation owner coordinates, shared helpers, `LaunchSlave` drive gate, `RunSlave` command gate before `DefineDosDevice`, stale direct `towupper(cmdline[5])` assignment removal, and split ledger fragment; `docs/plan/check-srev-201.sh` is the targeted wrapper. Runtime/build gate: Windows service build plus valid mapped-drive broadcast and malformed NetProxy command smoke. |
