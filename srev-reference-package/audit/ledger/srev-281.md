---
kind: srev-ledger-entry
id: SREV-281
title: Net Param Device-Control Compartment Boundary
status: patched-comment-topology-after-official-device-control-icmp-review-no-behavior-change
owner: Sandboxie/core/dll/file_init.c
spec: docs/plan/srev-281-net-param-device-control-compartment-boundary.md
schema: docs/plan/srev-281-net-param-device-control-compartment-boundary.schema.json
checker: docs/plan/check-srev-281.py
runtime_gate: Windows network BlockNetParam and compartment-mode ICMP matrix
---

### SREV-281: Net Param Device-Control Compartment Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official device-control and ICMP review; no behavior change |
| Evidence | `File_Init` registers the `NtDeviceIoControlFile` hook only when `Dll_CompartmentMode` is false and `BlockNetParam` is enabled. `File_NtDeviceIoControlFile` then denies only selected TCP/NSI network-parameter IOCTLs after confirming the handle path is `\Device\TCP` or `\Device\NSI`. `IpHlp_Init` also skips ICMP helper hooks in compartment mode. The old inline comment said only that ping would otherwise fail, which hid the hook-registration owner and the compartment-mode native route. |
| Data | `Dll_CompartmentMode`, `SetCompartmentMode`, `SBIE_FLAG_APP_COMPARTMENT`, `BlockNetParam`, `File_IsBlockedNetParam`, `SBIEDLL_HOOK(File_,NtDeviceIoControlFile)`, `File_NtDeviceIoControlFile`, `IoControlCode`, `0x00128004`, `0x00120013`, `\Device\TCP`, `\Device\NSI`, `IpHlp_Init`, `IcmpCreateFile`, and `IcmpSendEcho`. |
| Schema | `NET_PARAM_DEVICE_CONTROL_COMPARTMENT_BOUNDARY` says `File_Init` owns `NtDeviceIoControlFile` hook registration for `BlockNetParam`; device-control calls send IOCTL codes to a device driver; `IoControlCode` determines the operation and buffer shape; private IOCTLs can be device-specific and must be classified locally; `BlockNetParam` registers the TCP/NSI deny hook only for non-compartment boxes; `File_NtDeviceIoControlFile` owns the TCP and NSI network-parameter IOCTL deny logic; compartment mode keeps the native device-control route for ICMP/IP helper behavior; `IpHlp_Init` skips ICMP helper hooks in compartment mode; this SREV changes comments and proof only. |
| Topology | `Dll_CompartmentMode true -> skip NtDeviceIoControlFile hook registration -> native IP helper/device-control route`. `Dll_CompartmentMode false + BlockNetParam true -> register File_NtDeviceIoControlFile hook -> inspect TCP/NSI IOCTLs -> deny matching network-parameter control calls -> pass all other device-control calls to __sys_NtDeviceIoControlFile`. |
| Logic Risk | Symptom-only wording can drive a future edit to enable the hook uniformly in compartment mode, hiding that the actual deny owner is the narrow TCP/NSI IOCTL filter and that compartment mode intentionally keeps native IP helper/device-control behavior. |
| Official Shape | Microsoft documents `ZwDeviceIoControlFile` / user-mode `NtDeviceIoControlFile` and Win32 `DeviceIoControl` as sending control codes to device drivers, with operation and buffer shape selected by the control code. Microsoft IOCTL documentation distinguishes public and private IOCTL shapes. Microsoft ICMP documentation records `IcmpCreateFile` and `IcmpSendEcho` as the IP Helper echo path. |
| Fix | Comment-only source clarification. The source now names SREV-281 and states that compartment mode keeps the native device-control route for ICMP/IP helper behavior, while the `BlockNetParam` TCP/NSI IOCTL deny hook belongs to non-compartment boxes. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-281.py` validates the draft-07 schema, official references, `File_Init` hook predicate, `File_IsBlockedNetParam` default, `File_NtDeviceIoControlFile` TCP/NSI IOCTL deny shape, `iphlp.c` compartment ICMP adjacency, stale source wording removal, and ledger fragment; `docs/plan/check-srev-281.sh` is the targeted wrapper. Runtime gate: Windows network matrix covering non-compartment `BlockNetParam=y` TCP/NSI denial, non-compartment `BlockNetParam=n` native pass-through, compartment-mode ICMP echo behavior, normal non-network `NtDeviceIoControlFile` pass-through, and monitor logging for denied network-parameter control calls. |
