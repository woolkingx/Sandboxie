---
kind: srev-ledger-entry
id: SREV-095
title: ARM64 API Instrumentation ABI
status: source-level-classified-after-official-windows-arm64-abi-arm64-exception-handlin
owner: "Sandboxie/core/dll/util_arm.asm:436"
spec: docs/plan/srev-095-arm64-api-instrumentation-abi.md
schema: docs/plan/srev-095-arm64-api-instrumentation-abi.schema.json
checker: docs/plan/check-srev-095.py
runtime_gate: "Windows ARM64 ApiTrace smoke where a traced API receives original `x0-x7` argument values, `ApiInstrumentation` logs the expected function name, `ReturnAddress` maps to the saved `LR`, recursion guard suppresses nested trace loops, and the final branch reaches the intended detour target"
---
### SREV-095: ARM64 API Instrumentation ABI

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official Windows ARM64 ABI, ARM64 exception handling, and Arm64EC ABI shape; comment-only source clarification, no behavior change |
| Evidence | `Sandboxie/core/dll/util_arm.asm:436` carried a bare `; todo` inside `ApiInstrumentationAsm`. Microsoft documents Windows ARM64 integer registers: `x0-x8` are volatile parameter/result registers, `x16-x17` are volatile intra-procedure-call scratch registers, `x18` points to the TEB in user mode, `x29/fp` is the frame pointer, and `x30/lr` is the link register. Local `dllhook.c` emits ARM64 trace detours with `x17` pointing at the trace entry header and `x16` pointing at `ApiInstrumentationAsm`. Local `trace.c` consumes `ApiInstrumentation(pName, pStack)` and reads `pStack[-1]` as `ReturnAddress`. |
| Data | ARM64 `Dll_ApiTrace` detour, trace entry header in `x17`, `ApiInstrumentationAsm`, saved `x0-x7` argument frame, saved `fp/lr`, saved `x16/x17`, `ApiInstrumentation(pName, pArgs)`, and final branch to detour target. |
| Schema | `ARM64_API_INSTRUMENTATION_ABI` says `dllhook.c` emits ARM64 trace detours with `x17` pointing at the trace entry header; `ApiInstrumentationAsm` preserves `x0-x7` before calling `ApiInstrumentation`; it passes `pName` in `x0` and the saved argument frame in `x1`; the saved argument frame begins at the saved `x0/x1` pair; `pArgs[-1]` is the saved `LR` consumed by `ApiInstrumentation` as `ReturnAddress`; `ApiInstrumentationAsm` preserves `x16/x17` across the call before branching to the detour target; `SP` remains 16-byte aligned across all stack accesses and the C call; this SREV does not change ApiTrace runtime behavior. |
| Topology | `Dll_ApiTrace` causes `dllhook.c` to emit a trace entry that loads `x17 = NewDetour`, loads `x16 = ApiInstrumentationAsm`, and branches to `x16`. The ARM64 proxy saves `x0-x7` and `fp/lr`, derives `pName = x17 + 8`, derives `pArgs = saved x0/x1 frame`, saves `x16/x17`, calls `ApiInstrumentation`, restores `x16/x17`, restores the original argument registers, loads the detour target from `[x17]`, and branches to that target. |
| Logic Risk | The stale TODO made a live ABI bridge look unfinished. Rewriting it as missing behavior would risk breaking ARM64 ApiTrace argument preservation. The local code already matches the official ABI shape: volatile argument registers are saved before the C call, volatile `x16/x17` trampoline state is saved across the C call, `SP` changes in 16-byte paired-store increments, and `pArgs[-1]` maps to the saved `LR` that `trace.c` expects as `ReturnAddress`. |
| Official Shape | `docs/plan/srev-095-arm64-api-instrumentation-abi.md` records Microsoft Windows ARM64 ABI conventions, ARM64 exception handling, and Arm64EC ABI references. `docs/plan/srev-095-arm64-api-instrumentation-abi.schema.json` records the JSON Schema draft-07 local `ARM64_API_INSTRUMENTATION_ABI` contract. |
| Fix | Comment-only source clarification: the stale `; todo` was replaced with the actual ABI contract for `x17`, saved `x0-x7`, and `pArgs[-1]`; the nearby section heading was corrected from `InstrumentationCallbackAsm` to `ApiInstrumentationProxy`. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-095.py` validates the draft-07 schema, official references, `dllhook.c` ARM64 trace-detour emission, `util_arm.asm` argument/scratch-register preservation, stale TODO removal, `trace.c` `ApiInstrumentation` `pStack[-1]` consumption, and ledger entry; `docs/plan/check-srev-095.sh` is the matrix wrapper. Runtime gate: Windows ARM64 ApiTrace smoke where a traced API receives original `x0-x7` argument values, `ApiInstrumentation` logs the expected function name, `ReturnAddress` maps to the saved `LR`, recursion guard suppresses nested trace loops, and the final branch reaches the intended detour target. |
