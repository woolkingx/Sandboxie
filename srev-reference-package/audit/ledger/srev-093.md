---
kind: srev-ledger-entry
id: SREV-093
title: Trace Instrumentation Private API Boundary
status: source-level-classified-after-official-public-process-information-token-privileg
owner: Sandboxie/core/dll/trace.c
spec: docs/plan/srev-093-trace-instrumentation-private-api-boundary.md
schema: docs/plan/srev-093-trace-instrumentation-private-api-boundary.schema.json
checker: docs/plan/check-srev-093.py
runtime_gate: "Windows matrix across Windows 7/8.1/10 build 10041+, x86/WOW64/x64/ARM64/ARM64EC, current-process versus driver-mediated setup, token privilege state, HVCI on/off where applicable, and `CallTraceEx` logging correctness before any driver or privilege behavior change"
---
### SREV-093: Trace Instrumentation Private API Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | source-level classified after official public process-information, token privilege, Arm64EC ABI, and context API shape; no behavior patch because the instrumentation class is private and runtime matrix is required |
| Evidence | `Sandboxie/core/dll/trace.c` installs optional `CallTraceEx` syscall instrumentation with `NtSetInformationProcess(ProcessInstrumentationCallback, ...)`. Microsoft documents public `SetProcessInformation` classes and access rights but does not define `ProcessInstrumentationCallback`; Microsoft documents `NtQueryInformationProcess` as internal and subject to change. The local enum value comes from `Sandboxie/common/win32_ntddk.h`, not a public API contract. The old source comments proposed using SbieDrv or privilege enablement for pre-10041 builds and left an ARM64EC TODO. |
| Data | `CallTraceEx` config, private `ProcessInstrumentationCallback` process-information class, local `PROCESS_INSTRUMENTATION_CALLBACK_INFORMATION`, `NtSetInformationProcess`, pre-10041 `SeDebugPrivilege` behavior, x86/WOW64/x64/ARM64/ARM64EC callback ABI, `RtlCaptureContext`, and `RtlRestoreContext`. |
| Schema | `TRACE_INSTRUMENTATION_PRIVATE_API_BOUNDARY` says `CallTraceEx` may request a process instrumentation callback only through the trace owner; `ProcessInstrumentationCallback` is a private `NtSetInformationProcess` class in this tree; public `SetProcessInformation` documentation does not define the instrumentation callback class; pre-10041 privilege behavior stays fail-closed until proven by runtime matrix; `AdjustTokenPrivileges` cannot add `SeDebugPrivilege` to a token that lacks it; driver-mediated privilege or temporary privilege enablement is not a source-only fix; ARM64EC is not covered by the native ARM64 callback restore path. |
| Topology | `Trace_Init` reads `CallTraceEx`, calls `InstallInstrumentationCallback`, builds a local callback-info struct, crosses the private `NtSetInformationProcess(ProcessInstrumentationCallback)` edge, then returns into `InstrumentationCallbackAsm` / `InstrumentationCallback` / `InstrumentationTrace` if the OS accepts it. The x86/WOW64 and pre-10041 paths fail closed; ARM64EC also fails closed. |
| Logic Risk | Treating the TODO as a direct implementation task would connect a private NT process-information class to either kernel driver policy or token privilege mutation without a public API contract. Public privilege APIs can enable existing privileges but cannot add missing privileges, and `SeDebugPrivilege` is high-trust state. ARM64EC is x64-compatible/thunked and cannot inherit the native ARM64 restore path by source analogy. |
| Official Shape | `docs/plan/srev-093-trace-instrumentation-private-api-boundary.md` records Microsoft `SetProcessInformation`, `NtQueryInformationProcess`, process access rights, `AdjustTokenPrivileges`, privilege constants, debug privilege, Arm64EC, Arm64EC ABI, `RtlCaptureContext`, and `RtlRestoreContext` references. `docs/plan/srev-093-trace-instrumentation-private-api-boundary.schema.json` records the JSON Schema draft-07 local `TRACE_INSTRUMENTATION_PRIVATE_API_BOUNDARY` contract. |
| Fix | Comment-only source clarification: the stale pre-10041 TODO is replaced with a private-API/fail-closed contract, and the ARM64EC TODO is replaced with an ABI-boundary note. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-093.py` validates the draft-07 schema, official references, private API classification, local enum ownership, pre-10041 fail-closed behavior, ARM64EC fail-closed behavior, stale TODO removal, and ledger entry; `docs/plan/check-srev-093.sh` is the matrix wrapper. Runtime gate: Windows matrix across Windows 7/8.1/10 build 10041+, x86/WOW64/x64/ARM64/ARM64EC, current-process versus driver-mediated setup, token privilege state, HVCI on/off where applicable, and `CallTraceEx` logging correctness before any driver or privilege behavior change. |
