# SREV-170: ARM64 Driver Assembly ABI Review

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> verify
input artifact: Sandboxie/core/drv/util_arm.asm, SboxDrv.vcxproj, token/syscall/driver call sites, and Microsoft ARM64 ABI documentation
output artifact: ARM64 driver assembly boundary is documented and source-gated; Windows ARM64 build/runtime proof remains open
owner: Sandboxie/core/drv/util_arm.asm
acceptance gate: docs/plan/check-srev-170.py and docs/plan/check-srev-170.sh
```

## Data

`util_arm.asm` is the ARM64 driver assembly bridge for three non-C call paths:

- `Sbie_InvokeSyscall_asm` calls an arbitrary kernel function pointer with up
  to 19 integer/pointer arguments from an array.
- `Sbie_SepFilterTokenHandler_asm` calls the unexported
  `Token_SepFilterToken` function with the 11-argument shape used by
  Sandboxie's token creation path.
- `Sbie_CallZwServiceFunction_asm` tail-jumps through `Driver_KiServiceInternal`
  after loading the 20th argument, the service number, into `x16`.

`SboxDrv.vcxproj` includes `util_arm.asm` only for `SbieDebug|ARM64` and
`SbieRelease|ARM64` through `armasm64`. This is a real ARM64 driver build
surface, not a dead file.

## Official Shape

- Microsoft documents the Windows ARM64 ABI as AArch64-based, with `x0-x8`
  volatile parameter/result scratch registers, `x9-x15` volatile scratch
  registers, `x16-x17` volatile intra-procedure-call scratch registers, `x29`
  as frame pointer, and `x30` as link register:
  `https://learn.microsoft.com/en-us/cpp/build/arm64-windows-abi-conventions?view=msvc-170`.
- The same Microsoft ABI page documents parameter assignment for integral or
  pointer types: arguments of 8 bytes or less use `x0` through `x7` while
  available; remaining stack arguments are assigned at the current stack
  argument address.
- The same page documents that the stack must remain 16-byte aligned on
  Windows ARM64, and notes kernel stack size constraints.
- Microsoft documents ARM64EC separately as an interoperability ABI. This
  driver project uses Classic ARM64 `armasm64` for `SbieDebug|ARM64` and
  `SbieRelease|ARM64`, not ARM64EC:
  `https://learn.microsoft.com/en-us/cpp/build/arm64ec-windows-abi-conventions?view=msvc-170`.

## Schema

`ARM64_DRIVER_ASM_ABI_REVIEW` says:

- `util_arm.asm` owns ARM64 driver assembly wrappers for syscall invocation,
  SepFilterToken invocation, and the KiServiceInternal service bridge.
- The ARM64 driver build surface is `SboxDrv.vcxproj` `SbieDebug|ARM64` and
  `SbieRelease|ARM64` using `armasm64`.
- `Sbie_InvokeSyscall_asm` may accept at most 19 arguments, maps the first eight
  array entries to `x0-x7`, and copies any higher arguments to the stack while
  preserving 16-byte stack alignment.
- `Sbie_SepFilterTokenHandler_asm` maps Sandboxie's five wrapper inputs into
  the 11-argument `Token_SepFilterToken` call shape: `TokenObject`, six zero
  arguments, `SidCount`, `SidPtr`, `LengthIncrease`, and `NewToken`.
- `Sbie_CallZwServiceFunction_asm` treats the 20th wrapper argument as the
  service number, loads it from `[sp,#0x58]` into `x16`, and tail-jumps to
  `Driver_KiServiceInternal`.
- Linux source gates are not ARM64 WDK build, unwind, or runtime proof.

## Topology

Legal ARM64 bridge topology:

```text
Syscall_Invoke
  -> Sbie_InvokeSyscall_asm(func, count, args)
  -> ARM64 integer/pointer ABI register + stack call

Sbie_SepFilterTokenHandler
  -> Sbie_SepFilterTokenHandler_asm(TokenObject, SidCount, SidPtr, LengthIncrease, NewToken)
  -> Token_SepFilterToken(TokenObject, 0, 0, 0, 0, 0, 0, SidCount, SidPtr, LengthIncrease, NewToken)

SbieCreateToken
  -> Sbie_CallZwServiceFunction_asm(arg1..arg19, svc_num)
  -> x16 = svc_num
  -> Driver_KiServiceInternal
```

These wrappers are ABI bridges. Their correctness is not defined by ordinary C
type checking; it is defined by the Windows ARM64 ABI, the call site contracts,
and ARM64 driver build/runtime behavior.

## Logic Risk

The file is high-risk because it is hand-written kernel-mode ARM64 assembly
that bypasses ordinary compiler argument lowering and unwind validation. A
mistake can corrupt syscall arguments, token creation arguments, stack
alignment, or the service number register. Source readback did not prove a
specific defect in this pass, but the file must remain explicitly covered and
must not be marked complete without ARM64 build/runtime proof.

## Action

No source patch is made in this SREV. The source-level action is to document the
ABI boundary, pin the build target, and add a checker that verifies the current
assembly still matches the local call-site topology and official ARM64 ABI
assumptions.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-170.py
bash docs/plan/check-srev-170.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-170.py &&
bash docs/plan/check-srev-170.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows ARM64 WDK driver build for `SbieDebug|ARM64` and
`SbieRelease|ARM64`; `Sbie_InvokeSyscall_asm` smoke with 0, 1, 8, 9, and 19
integer/pointer arguments; token creation smoke through
`Sbie_SepFilterTokenHandler_asm`; `SbieCreateToken` smoke through
`Sbie_CallZwServiceFunction_asm`; unwind/stack trace sanity around each wrapper.
