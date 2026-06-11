---
kind: srev-ledger-entry
id: SREV-177
title: ARM64EC API Instrumentation Argument Preservation
status: patched-source-level-after-official-arm64ec-abi-review-needs-windows-arm64ec-build-runtime-proof
owner: Sandboxie/core/dll/util_EC.asm
spec: docs/plan/srev-177-arm64ec-api-instrumentation-argument-preservation.md
schema: docs/plan/srev-177-arm64ec-api-instrumentation-argument-preservation.schema.json
checker: docs/plan/check-srev-177.py
runtime_gate: "Windows ARM64EC SboxDll build plus API trace smoke with eight integer pointer arguments and RPC NDR hook smoke"
---

### SREV-177: ARM64EC API Instrumentation Argument Preservation

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ARM64EC ABI review; needs Windows ARM64EC build/runtime proof |
| Evidence | `Sandboxie/core/dll/util_EC.asm` was the highest-ranked unnamed reviewable core file after SREV-176. `SboxDll.vcxproj` builds `util_asm.asm` for ARM64EC with `_M_ARM64EC`, selecting this assembly path. `dllhook.c` emits API trace detours that branch through `ApiInstrumentationAsm`, while `trace.c` `ApiInstrumentation` consumes the saved argument frame and `pStack[-1]` return address. Before this SREV, the ARM64EC API instrumentation bridge saved only `x0-x3` before the C call, while native ARM64 `util_arm.asm` saved `x0-x7` for the same trace topology. |
| Data | `Sandboxie/core/dll/util_EC.asm`, `Sandboxie/core/dll/util_arm.asm`, `Sandboxie/core/dll/dllhook.c`, `Sandboxie/core/dll/trace.c`, `Sandboxie/core/dll/SboxDll.vcxproj`, `ApiInstrumentationAsm`, `ApiInstrumentation`, `x0` through `x7`, `x16`, `x17`, `fp`, `lr`, and ARM64EC variadic NDR wrappers. |
| Schema | `ARM64EC_API_INSTRUMENTATION_ARGUMENT_PRESERVATION` says `util_EC.asm` owns ARM64EC API instrumentation assembly state preservation; `dllhook.c` emits trace detours with `x17` pointing at the trace entry header; `ApiInstrumentationAsm` preserves `x0-x7`, passes `pName` in `x0` and the saved argument frame in `x1`, preserves `x16/x17`, keeps `SP` 16-byte aligned, and leaves the ARM64EC RPC NDR variadic stack pointer/size contract unchanged. |
| Topology | Legal API trace flow is `dllhook.c trace detour -> x17 trace entry -> ApiInstrumentationAsm -> save x0-x7/fp/lr -> ApiInstrumentation(pName, pArgs) -> restore x0-x7/fp/lr/x16/x17 -> branch to [x17] detour target`. RPC NDR wrappers remain on their separate ARM64EC variadic route where `x4` points at the first stack parameter and `x5` carries stack-parameter byte size. |
| Logic Risk | `ApiInstrumentation` is an ordinary C call. If the trace trampoline saves only `x0-x3`, a traced target whose fifth through eighth integer/pointer arguments arrive in `x4-x7` can receive corrupted argument values after tracing. This is trace-only and ARM64EC-specific, which makes it easy to miss without explicit ABI/schema review. |
| Official Shape | `docs/plan/srev-177-arm64ec-api-instrumentation-argument-preservation.md` records Microsoft ARM64EC interoperability, ARM64EC ABI, Windows ARM64 ABI, and ARM64EC ABI helper references. `docs/plan/srev-177-arm64ec-api-instrumentation-argument-preservation.schema.json` records the JSON Schema draft-07 local `ARM64EC_API_INSTRUMENTATION_ARGUMENT_PRESERVATION` contract. |
| Fix | `ApiInstrumentationAsm` now spills and restores `x6/x7` and `x4/x5` around the `ApiInstrumentation` call. `pArgs` still points at the saved `x0/x1` pair, and `pArgs[-1]` still resolves to the saved `LR`. No RPC wrapper, trace entry layout, monitor log path, instrumentation callback policy, or native ARM64 assembly changed. |
| Acceptance Gate | `docs/plan/check-srev-177.py` validates the draft-07 schema, official references, ARM64EC `ApiInstrumentationAsm` `x0-x7` preservation, native ARM64 comparison shape, untouched ARM64EC variadic NDR wrapper comments, ARM64EC assembly build inclusion, dllhook trace detour emission, trace consumer shape, RPC wrapper consumer shape, and ledger fragment; `docs/plan/check-srev-177.sh` is the matrix wrapper. Runtime/build gate: Windows ARM64EC `SboxDll` build; API trace smoke on a traced function with at least eight integer/pointer arguments proving `x0-x7` reach the final detour target unchanged; monitor log proving `ApiInstrumentation` still receives expected function name and return address; RPC NDR hook smoke proving variadic wrapper behavior is unchanged. |
