---
kind: srev-ledger-entry
id: SREV-153
title: Spooler Counted Port Name
status: patched-source-level-after-official-object-name-and-spooler-rpc-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/ipc_spl.c
spec: docs/plan/srev-153-spooler-counted-port-name.md
schema: docs/plan/srev-153-spooler-counted-port-name.schema.json
checker: docs/plan/check-srev-153.py
runtime_gate: Windows spooler endpoint counted-name and RPC policy runtime proof
---

### SREV-153: Spooler Counted Port Name

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official object-name / `UNICODE_STRING` / MS-RPRN review; needs Windows spooler endpoint runtime proof |
| Evidence | `Sandboxie/core/drv/ipc_spl.c` was the top unnamed reviewable core file after SREV-152. It owns the print spooler endpoint gate before the RPC opnum policy runs. Before this SREV, both the Windows 8.1+ dynamic spooler port branch and the Vista+ `\RPC Control\spoolss` branch compared `Name->Name.Buffer` with `_wcsicmp`, treating `OBJECT_NAME_INFORMATION.Name.Buffer` as a C string instead of a counted `UNICODE_STRING`. |
| Data | `Ipc_CheckPortRequest_SpoolerPort`, `Ipc_Spl_MatchPortName`, `OBJECT_NAME_INFORMATION.Name`, `UNICODE_STRING.Length`, `UNICODE_STRING.Buffer`, `Ipc_Dynamic_Ports.pSpoolerPort->wstrPortName`, `\RPC Control\spoolss`, `Ipc_GetRpcMsgId`, `Ipc_Filter_Spooler_Msg`, and MS-RPRN spooler RPC opnums. |
| Schema | `IPC_SPOOLER_COUNTED_PORT_NAME` says `OBJECT_NAME_INFORMATION.Name` is a counted `UNICODE_STRING`, `UNICODE_STRING.Length` is a byte count and does not authorize C-string scans over `Name->Name.Buffer`, spooler endpoint matching uses `RtlEqualUnicodeString` with `RtlInitUnicodeString` only for expected NUL-terminated names, the Windows 8.1+ dynamic branch still accepts only the cached dynamic spooler port, the Vista+ branch still accepts only `\RPC Control\spoolss`, and this SREV does not change KPATH-006 RPC payload capture, spooler opnum filtering, dynamic-port publication, `OpenPrintSpooler`, or `AllowSpoolerPrintToFile` behavior. |
| Topology | Legal flow is object manager, `OBJECT_NAME_INFORMATION.Name`, counted spooler endpoint match through `Ipc_Spl_MatchPortName`, KPATH-006 `Ipc_GetRpcMsgId` payload capture, then `Ipc_Filter_Spooler_Msg` MS-RPRN opnum policy. |
| Logic Risk | The old port-name gates crossed from counted kernel object-name data to NUL-terminated C-string comparison before the spooler policy decision. Even if common object-name query paths often include a trailing NUL, `UNICODE_STRING.Length` remains the authoritative extent for the policy input. |
| Official Shape | `docs/plan/srev-153-spooler-counted-port-name.md` records Microsoft `ObQueryNameString`, `UNICODE_STRING`, `RtlEqualUnicodeString`, `RtlInitUnicodeString`, and MS-RPRN references. `docs/plan/srev-153-spooler-counted-port-name.schema.json` records the JSON Schema draft-07 local `IPC_SPOOLER_COUNTED_PORT_NAME` contract. |
| Fix | `ipc_spl.c` now has `Ipc_Spl_MatchPortName`, which initializes the expected port name as a `UNICODE_STRING` and compares it with `Name->Name` using `RtlEqualUnicodeString(..., TRUE)`. The dynamic spooler port branch and legacy `\RPC Control\spoolss` branch no longer call `_wcsicmp` on `Name->Name.Buffer`. |
| Acceptance Gate | `docs/plan/check-srev-153.py` validates the draft-07 schema, official references, counted spooler port-name helper, removal of `_wcsicmp` object-name comparison from `ipc_spl.c`, preservation of KPATH-006 `Ipc_GetRpcMsgId` routing, preservation of the existing spooler opnum deny table, and the ledger fragment; `docs/plan/check-srev-153.sh` is the matrix wrapper. Runtime/build gate: Windows driver build for `ipc_spl.c`; object-name instrumentation proving dynamic spooler and `\RPC Control\spoolss` endpoint names match by counted length, including buffers without a trailing NUL; normal spooler print traffic; blocked mutating MS-RPRN operations; unchanged KPATH-006 RPC payload-shape capture. |
