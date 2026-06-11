---
kind: srev-ledger-entry
id: SREV-170
title: ARM64 Driver Assembly ABI Review
status: source-reviewed-needs-arm64-build-runtime
owner: Sandboxie/core/drv/util_arm.asm
spec: docs/plan/srev-170-arm64-driver-asm-abi-review.md
schema: docs/plan/srev-170-arm64-driver-asm-abi-review.schema.json
checker: docs/plan/check-srev-170.py
runtime_gate: "Windows ARM64 WDK driver build for SbieDebug ARM64 and SbieRelease ARM64, Sbie_InvokeSyscall_asm 0/1/8/9/19 argument smoke, token creation smoke, SbieCreateToken service bridge smoke, and unwind/stack trace sanity"
---

### SREV-170: ARM64 Driver Assembly ABI Review

| Field | Content |
|---|---|
| Severity | [major] |
| Status | source reviewed after Microsoft ARM64 ABI and local ARM64 driver build-surface review; no source patch; needs Windows ARM64 build/runtime proof |
| Evidence | `Sandboxie/core/drv/util_arm.asm` was the top unnamed reviewable core file after SREV-169. `Sandboxie/core/drv/SboxDrv.vcxproj` builds it with `armasm64` for `SbieDebug|ARM64` and `SbieRelease|ARM64`. It exports `Sbie_InvokeSyscall_asm`, `Sbie_SepFilterTokenHandler_asm`, and `Sbie_CallZwServiceFunction_asm`, which are referenced from `syscall.c`, `token.c`, and ARM64 token creation paths in `driver.c` / `token.c`. |
| Data | `Sandboxie/core/drv/util_arm.asm`, `Sandboxie/core/drv/SboxDrv.vcxproj`, `Sandboxie/core/drv/syscall.c`, `Sandboxie/core/drv/token.c`, `Sandboxie/core/drv/driver.c`, `Sbie_InvokeSyscall_asm`, `Sbie_SepFilterTokenHandler_asm`, `Sbie_CallZwServiceFunction_asm`, `Token_SepFilterToken`, `Driver_KiServiceInternal`, `SbieCreateToken`, `Syscall_Invoke`, `armasm64`, `ARM64`, `x0`, `x7`, `x16`, `x29`, and `x30`. |
| Schema | `ARM64_DRIVER_ASM_ABI_REVIEW` says `util_arm.asm` owns the ARM64 driver assembly wrappers; `SboxDrv.vcxproj` builds it only for ARM64 with `armasm64`; `Sbie_InvokeSyscall_asm` maps up to 19 integer/pointer arguments through `x0-x7` and stack slots; `Sbie_SepFilterTokenHandler_asm` maps five wrapper inputs into the 11-argument `Token_SepFilterToken` shape; and `Sbie_CallZwServiceFunction_asm` loads the 20th argument from `[sp,#0x58]` into `x16` before tail-jumping to `Driver_KiServiceInternal`. |
| Topology | Legal flow is `Syscall_Invoke` -> `Sbie_InvokeSyscall_asm` -> ARM64 ABI call; `Sbie_SepFilterTokenHandler` -> `Sbie_SepFilterTokenHandler_asm` -> `Token_SepFilterToken(TokenObject, 0, 0, 0, 0, 0, 0, SidCount, SidPtr, LengthIncrease, NewToken)`; and `SbieCreateToken` -> `Sbie_CallZwServiceFunction_asm(arg1..arg19, svc_num)` -> `x16 = svc_num` -> `Driver_KiServiceInternal`. |
| Logic Risk | The file is high-risk hand-written kernel ARM64 assembly. A bad register, stack, frame, or service-number mapping can corrupt syscall invocation, token creation, or ARM64 service bridge behavior. This pass found a coherent source-level ABI shape, but source readback alone cannot prove ARM64 assembler output, unwind behavior, or runtime correctness. |
| Official Shape | `docs/plan/srev-170-arm64-driver-asm-abi-review.md` records Microsoft ARM64 and ARM64EC ABI references. `docs/plan/srev-170-arm64-driver-asm-abi-review.schema.json` records the JSON Schema draft-07 local `ARM64_DRIVER_ASM_ABI_REVIEW` contract. |
| Fix | No source patch. The action is coverage, ABI documentation, and source gating for the existing ARM64 driver assembly bridge. |
| Acceptance Gate | `docs/plan/check-srev-170.py` validates the draft-07 schema, official references, ARM64 build target, exported assembly wrappers, argument/register/stack bridge shape, call-site topology, and ledger entry; `docs/plan/check-srev-170.sh` is the matrix wrapper. Runtime/build gate: Windows ARM64 WDK driver build for `SbieDebug|ARM64` and `SbieRelease|ARM64`; `Sbie_InvokeSyscall_asm` smoke with 0, 1, 8, 9, and 19 integer/pointer arguments; token creation smoke through `Sbie_SepFilterTokenHandler_asm`; `SbieCreateToken` smoke through `Sbie_CallZwServiceFunction_asm`; unwind/stack trace sanity around each wrapper. |
