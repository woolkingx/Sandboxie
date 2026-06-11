---
kind: srev-ledger-entry
id: SREV-067
title: Secure UAC Packet Input Gate
status: patched-source-level-after-official-wcslen-wmemcpy-input-shape-and-local-uac-pac
owner: Sandboxie/core/dll/secure.c
spec: docs/plan/srev-067-secure-uac-packet-input-gate.md
schema: docs/plan/srev-067-secure-uac-packet-input-gate.schema.json
checker: docs/plan/check-srev-067.py
runtime_gate: normal AppInfo type 1 elevation, MSI type 2 elevation, malformed type 1 missing-string paths, and low-memory packet allocation failure
---
### SREV-067: Secure UAC Packet Input Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `wcslen`/`wmemcpy` input-shape and local UAC packet builder analysis; needs Windows UAC AppInfo runtime proof |
| Evidence | `Sandboxie/core/dll/secure.c` type 1 UAC elevation classification checked `ProcessHandle` but did not prove `ApplicationName`, `CommandLine`, or `CurrentDirectory` before setting `Secure_Elevation_Type = 1`. `Secure_HandleElevation` then called `wcslen` and `wmemcpy` on those pointers. Microsoft documents `wcslen` as operating on a null-terminated wide string and `wmemcpy` as copying from source to destination buffers. The packet builder also wrote to `pkt` immediately after `Dll_Alloc(pkt_len)` without checking allocation success. |
| Data | Type 1 `SECURE_UAC_ARGS` string pointers, type 1 result-handle pointer, global elevation type state, `SECURE_UAC_PACKET` allocation, length pass, and packet serialization pass. |
| Schema | `SECURE_UAC_PACKET_INPUT_GATE` says type 1 elevation may be classified only after `ProcessHandle`, `ApplicationName`, `CommandLine`, and `CurrentDirectory` are non-null; packet serialization may start only after allocation succeeds. |
| Topology | NDR stack arguments flow through `Secure_CheckElevation` type classification, then through `Secure_HandleElevation` packet construction, then to the service UAC request. The classifier owns the type 1 argument-shape gate; the packet builder owns allocation proof. |
| Logic Risk | A malformed or drifted AppInfo RPC stack shape should fail closed before Sandboxie records global elevation state. Otherwise a partially recognized elevation call can crash in string length/copy or write through a null packet allocation. |
| Official Shape | `docs/plan/srev-067-secure-uac-packet-input-gate.md` records Microsoft `wcslen` and `wmemcpy` references. `docs/plan/srev-067-secure-uac-packet-input-gate.schema.json` records the JSON Schema draft-07 local `SECURE_UAC_PACKET_INPUT_GATE` contract. |
| Fix | Type 1 classification now requires non-null `ApplicationName`, `CommandLine`, and `CurrentDirectory` before assigning `Secure_Elevation_Type = 1`. Packet construction now returns immediately if `Dll_Alloc(pkt_len)` fails. |
| Acceptance Gate | `docs/plan/check-srev-067.py` validates the draft-07 schema, official references, string-pointer gates before type assignment, allocation gate before packet writes, and ledger entry; `docs/plan/check-srev-067.sh` is the matrix wrapper. Windows gate: normal AppInfo type 1 elevation, MSI type 2 elevation, malformed type 1 missing-string paths, and low-memory packet allocation failure. |
