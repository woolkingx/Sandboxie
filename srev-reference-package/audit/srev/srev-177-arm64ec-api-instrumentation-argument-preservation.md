# SREV-177: ARM64EC API Instrumentation Argument Preservation

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/util_EC.asm, util_arm.asm, dllhook.c, trace.c, SboxDll.vcxproj, Microsoft ARM64EC / ARM64 ABI documentation
output artifact: ARM64EC API trace trampoline preserves x0-x7 before calling ApiInstrumentation
owner: Sandboxie/core/dll/util_EC.asm
acceptance gate: docs/plan/check-srev-177.py and docs/plan/check-srev-177.sh
```

## Data

`util_EC.asm` is the ARM64EC DLL assembly bridge for RPC NDR hooks,
instrumentation-callback glue, and API trace detours. `SboxDll.vcxproj` builds
`util_asm.asm` for ARM64EC with `_M_ARM64EC`, which selects this file through
the project assembly include flow.

`dllhook.c` emits API trace detours that load the trace entry header into `x17`,
load `ApiInstrumentationAsm` into `x16`, and branch to it. `trace.c`
`ApiInstrumentation` receives `pName` and the saved argument frame, then reads
`pStack[-1]` as the original return address.

Before this SREV, the ARM64EC `ApiInstrumentationAsm` saved only `x0-x3` before
calling the C instrumentation function. Native ARM64 `util_arm.asm` already
saved `x0-x7` for the same API trace topology.

## Official Shape

- Microsoft documents ARM64EC as interoperating with x64 code while using
  ARM64EC-specific ABI additions:
  `https://learn.microsoft.com/en-us/windows/arm/arm64ec`.
- Microsoft documents that Arm64EC follows the classic ARM64 ABI calling
  convention except for variadic functions, and its variadic rule uses only
  `x0-x3` for parameters while `x4` points at the first stack parameter and
  `x5` carries the stack-parameter byte size:
  `https://learn.microsoft.com/en-us/windows/arm/arm64ec-abi`.
  In that variadic-only case, "Only the first four registers are used for
  parameter passing".
- Microsoft documents ARM64 parameter passing for non-variadic calls through the
  Windows ARM64 ABI:
  `https://learn.microsoft.com/en-us/cpp/build/arm64-windows-abi-conventions?view=msvc-170`.
- Microsoft documents ARM64EC ABI helpers and call checkers as preserving
  parameter registers such as `x0-x8` when forwarding calls:
  `https://learn.microsoft.com/en-us/cpp/build/arm64ec-windows-abi-conventions?view=msvc-170`.

The legal shape for an arbitrary API trace detour is therefore broader than the
RPC NDR variadic wrapper shape. API trace may forward non-variadic functions
whose fifth through eighth integer or pointer arguments are in `x4-x7`.

## Schema

`ARM64EC_API_INSTRUMENTATION_ARGUMENT_PRESERVATION` says:

- `util_EC.asm` owns ARM64EC API instrumentation assembly state preservation.
- `dllhook.c` emits ARM64EC API trace detours with `x17` pointing at the trace
  entry header and `x16` pointing at `ApiInstrumentationAsm`.
- `ApiInstrumentationAsm` must preserve `x0-x7` before calling
  `ApiInstrumentation`.
- `ApiInstrumentationAsm` passes `pName` in `x0` and the saved argument frame in
  `x1`.
- The saved argument frame begins at the saved `x0/x1` pair, and `pArgs[-1]` is
  the saved `LR` consumed as `ReturnAddress`.
- `ApiInstrumentationAsm` preserves `x16/x17` across the instrumentation call
  before loading the detour target from `[x17]`.
- `ApiInstrumentationAsm` keeps `SP` 16-byte aligned across stack accesses and
  the C call.
- RPC NDR ARM64EC wrappers keep their ARM64EC variadic stack pointer/size
  contract and are not changed by this SREV.
- SREV-177 does not change trace entry layout, monitor logging, RPC hook
  policy, instrumentation callback policy, or ARM64 native `util_arm.asm`.
- Linux source gates are not Windows ARM64EC build/runtime proof.

## Topology

Legal API trace topology after this SREV:

```text
dllhook.c API trace detour
  -> x17 = trace entry header
  -> x16 = ApiInstrumentationAsm
  -> ApiInstrumentationAsm saves x0-x7 and fp/lr
  -> x0 = x17 + 8 as pName
  -> x1 = saved x0/x1 frame as pArgs
  -> save x16/x17
  -> bl ApiInstrumentation
  -> restore x16/x17, fp/lr, x0-x7
  -> ldr x16, [x17]
  -> br x16 to detour target
```

RPC NDR wrapper topology remains separate:

```text
ARM64EC variadic NDR wrapper
  -> x0-x3 carry fixed/leading parameters
  -> x4 points at the first stack parameter
  -> x5 carries stack-parameter byte size
```

## Logic Risk

`ApiInstrumentation` is an ordinary C call. The ARM64EC ABI treats the argument
registers as volatile across such a call. If the trace trampoline saves only
`x0-x3`, a traced target whose fifth through eighth integer/pointer parameters
arrive in `x4-x7` can receive corrupted argument values after tracing. That is a
trace-only behavior bug: it appears only when API tracing is enabled and only on
ARM64EC paths with enough register arguments.

The minimal repair is to make ARM64EC API instrumentation match the already
reviewed native ARM64 trace trampoline preservation range, while leaving the
RPC NDR variadic wrappers alone.

## Action

`ApiInstrumentationAsm` now spills and restores `x6/x7` and `x4/x5` around the
`ApiInstrumentation` call. Its `pArgs` pointer still begins at the saved `x0/x1`
pair, and `pArgs[-1]` still resolves to the saved `LR`.

No RPC wrapper, trace entry layout, monitor log path, instrumentation callback
policy, or native ARM64 assembly changed.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-177.py
bash docs/plan/check-srev-177.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-177.py &&
bash docs/plan/check-srev-177.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows ARM64EC `SboxDll` build; API trace smoke on a
traced function with at least eight integer/pointer arguments proving `x0-x7`
reach the final detour target unchanged; monitor log proving
`ApiInstrumentation` still receives the expected function name and return
address; RPC NDR hook smoke proving variadic wrapper behavior is unchanged.
