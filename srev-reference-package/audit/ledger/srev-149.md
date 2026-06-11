---
kind: srev-ledger-entry
id: SREV-149
title: Kernel Time Hook Output Gate
status: patched-source-level-after-official-time-api-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/kernel.c
spec: docs/plan/srev-149-kernel-time-hook-output-gate.md
schema: docs/plan/srev-149-kernel-time-hook-output-gate.schema.json
checker: docs/plan/check-srev-149.py
runtime_gate: Windows DLL build and UseChangeSpeed time-scaling runtime proof
---

### SREV-149: Kernel Time Hook Output Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `QueryUnbiasedInterruptTime` / `QueryPerformanceCounter` and local `UseChangeSpeed` settings review; needs Windows DLL runtime proof |
| Evidence | `Sandboxie/core/dll/kernel.c` was the top unnamed reviewable core file after SREV-148. Its `UseChangeSpeed` branch hooks Win32 time APIs and transforms outputs according to `AddTickSpeed` / `LowTickSpeed`, which `Sandboxie/install/SbieSettings.ini` defines as zero-or-positive integers gated by `UseChangeSpeed=y`. Before this SREV, `Kernel_QueryUnbiasedInterruptTime` called the real API and then unconditionally dereferenced `UnbiasedTime`, even though Microsoft documents failure when the pointer is null. It also used `*UnbiasedTime *= add / low`, so fractional ratios such as `1/2` were integer-divided to zero before multiplication. The adjacent `Kernel_QueryPerformanceCounter` hook used multiply-before-divide arithmetic but still wrote its output pointer after a failed real API call. |
| Data | `UseChangeSpeed`, `AddTickSpeed`, `LowTickSpeed`, real API return status, `QueryUnbiasedInterruptTime(PULONGLONG UnbiasedTime)`, and `QueryPerformanceCounter(LARGE_INTEGER *lpPerformanceCount)`. |
| Schema | `KERNEL_TIME_HOOK_OUTPUT_GATE` says `UseChangeSpeed` hooks may transform only successful real API outputs, failed calls must propagate without Sandboxie-side output writes, null `QueryUnbiasedInterruptTime` pointers must not be dereferenced after failure, fractional ratios must use multiply-before-divide arithmetic, and the existing zero-add/zero-low fallback branch is not redefined here. |
| Topology | Legal flow is sandboxed time query, Kernel_ hook, real Kernel32/KernelBase API output, success/non-null gate, local `AddTickSpeed` / `LowTickSpeed` transform, then return with the real API status. |
| Logic Risk | The hook is a compatibility projection over official time APIs. Writing output after failure can turn a legal failure into an invalid write, and pre-dividing the configured ratio can collapse valid slow-down settings to zero time progression. |
| Official Shape | `docs/plan/srev-149-kernel-time-hook-output-gate.md` records Microsoft `QueryUnbiasedInterruptTime` and `QueryPerformanceCounter` references. `docs/plan/srev-149-kernel-time-hook-output-gate.schema.json` records the JSON Schema draft-07 local `KERNEL_TIME_HOOK_OUTPUT_GATE` contract. |
| Fix | `Kernel_QueryUnbiasedInterruptTime` now returns immediately when the real API fails or the output pointer is null, then applies `*UnbiasedTime = *UnbiasedTime * add / low` for nonzero ratios. `Kernel_QueryPerformanceCounter` now uses the same success/non-null output gate before applying its existing multiply-before-divide ratio. |
| Acceptance Gate | `docs/plan/check-srev-149.py` validates the draft-07 schema, official references, local settings evidence, source success/non-null gates, multiply-before-divide arithmetic, removal of the pre-divide expression, and the ledger fragment; `docs/plan/check-srev-149.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build; with `UseChangeSpeed=y`, `AddTickSpeed=1`, `LowTickSpeed=2`, unbiased interrupt time and performance counter values continue progressing at half speed rather than collapsing to zero; null/failing output paths preserve the real API failure without a Sandboxie-side output dereference. |
