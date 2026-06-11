# SREV-149: Kernel Time Hook Output Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/kernel.c`, `Sandboxie/install/SbieSettings.ini`, Microsoft `QueryUnbiasedInterruptTime` and `QueryPerformanceCounter` references |
| Output artifact | `docs/plan/srev-149-kernel-time-hook-output-gate.schema.json`, `docs/plan/check-srev-149.py`, `docs/plan/check-srev-149.sh`, ledger fragment |
| Owner | DLL-side `UseChangeSpeed` time hook surface |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows build/runtime proof remains required |

## Evidence

`Sandboxie/core/dll/kernel.c` is the top unnamed reviewable core file after
SREV-148. Its `UseChangeSpeed` branch hooks Win32 time APIs so sandboxed
processes can observe configured tick, sleep, and timer rates. The local
settings surface defines `AddTickSpeed` and `LowTickSpeed` as zero-or-positive
integers gated by `UseChangeSpeed=y`.

Before this SREV, `Kernel_QueryUnbiasedInterruptTime` called the real API, then
unconditionally dereferenced `UnbiasedTime`. It also used:

```c
*UnbiasedTime *= add / low;
```

That computes `add / low` before multiplying. A valid fractional speed such as
`AddTickSpeed=1` and `LowTickSpeed=2` therefore becomes zero instead of half
speed. The adjacent `Kernel_QueryPerformanceCounter` hook already uses
`value * add / low`, but it also wrote the output pointer after the real API
returned failure.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-queryunbiasedinterrupttime
- https://learn.microsoft.com/en-us/windows/win32/api/profileapi/nf-profileapi-queryperformancecounter

## Data

`UseChangeSpeed`, `AddTickSpeed`, `LowTickSpeed`,
`QueryUnbiasedInterruptTime(PULONGLONG UnbiasedTime)`,
`QueryPerformanceCounter(LARGE_INTEGER *lpPerformanceCount)`, real API return
status, and caller-owned output pointers.

## Schema

`KERNEL_TIME_HOOK_OUTPUT_GATE` says:

- `UseChangeSpeed` time hooks may transform only a successful real API output.
- A failed real API call must propagate the failure return without writing the
  output pointer in Sandboxie's hook.
- `QueryUnbiasedInterruptTime` reports failure when called with a null pointer;
  the hook must not dereference that pointer after failure.
- Fractional configured speed ratios must preserve multiply-before-divide
  arithmetic: `value * AddTickSpeed / LowTickSpeed`.
- Zero `AddTickSpeed` or zero `LowTickSpeed` follows the existing local fallback
  branch and is not redefined by this SREV.

## Topology

Legal flow:

```text
sandboxed process time query
  -> Kernel_ hook
  -> real Kernel32/KernelBase API writes caller-owned output
  -> hook verifies success and non-null output pointer
  -> hook applies local AddTickSpeed / LowTickSpeed transform
  -> caller receives transformed output with the real API return status
```

## Logic Risk

The hook owns a compatibility projection, not the official API contract. If it
writes output after the real API reports failure, it can turn a valid failure
shape into an invalid write. If it divides before multiplying, valid slow-down
settings collapse counters to zero, which can break code that expects monotonic
time progression.

## Fix

`Kernel_QueryUnbiasedInterruptTime` now returns immediately when the real API
fails or the output pointer is null, then applies `*UnbiasedTime =
*UnbiasedTime * add / low` for nonzero ratios. `Kernel_QueryPerformanceCounter`
now uses the same success/non-null output gate before applying its existing
multiply-before-divide ratio.

## Acceptance Gate

`docs/plan/check-srev-149.py` validates the draft-07 schema, official
references, local settings evidence, source success/non-null gates, preserved
multiply-before-divide ratio, removed pre-divide `*=` expression, and the
ledger fragment. `docs/plan/check-srev-149.sh` is the matrix wrapper.

Runtime/build gate: Windows DLL build; with `UseChangeSpeed=y`,
`AddTickSpeed=1`, `LowTickSpeed=2`, both unbiased interrupt time and
performance counter values continue progressing at half speed rather than
collapsing to zero; null/failing output paths preserve the real API failure
without a Sandboxie-side output dereference.
