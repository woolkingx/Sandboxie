---
kind: local-test-entry
id: LTEST-001
title: Sandboxie Test Parameter Verification Gate
status: patched-source-level-needs-windows-build-runtime-proof
owner: Sandboxie/core/drv/util.c
paths:
  - Sandboxie/core/drv/util.h
  - Sandboxie/core/drv/process.c
  - Sandboxie/core/drv/api.c
spec: docs/plan/local/ltest-001-sandboxie-test-parameter-verification-gate.md
schema: docs/plan/local/ltest-001-sandboxie-test-parameter-verification-gate.schema.json
checker: docs/plan/local/check-ltest-001.py
runtime_gate: Windows driver build plus Sandboxie.ini Test=true smoke proving unsigned local development caller APIs, process feature gates, and feature flags are locally bypassed while driver loading still uses the OS signing environment
---
### LTEST-001: Sandboxie Test Parameter Verification Gate

| Field | Content |
|---|---|
| Severity | [low] |
| Status | patched source-level local test gate; needs Windows build/runtime proof |
| Evidence | The local test workflow needs patched Sandboxie code to run without being blocked by Sandboxie's own caller-signature and supporter-certificate gates. Windows driver image loading is outside driver runtime and cannot be bypassed by code that has not yet loaded. This entry is local-only and not an SREV. |
| Data | `Test=true`, `MyIsTestMode`, `MyIsCallerSigned`, `Driver_OsTestSigning`, `Verify_CertInfo`, `Process_Create`, `Api_QueryDriverInfo`, and `SBIE_FEATURE_FLAG_*`. |
| Schema | `SANDBOXIE_TEST_PARAMETER_VERIFICATION_GATE` says `Test=true` is a local Sandboxie runtime setting, not a Windows loader signing control; `MyIsTestMode` is the single kernel helper that parses the global `Test` setting; accepted true spellings are `true`, `yes`, `y`, `1`, and `on`; `MyIsCallerSigned` treats `Test=true` as a local development caller-signature bypass; `Process_Create` treats `Test=true` as a local pass for supporter-certificate security and encryption gates; `Api_QueryDriverInfo` projects `Test=true` into driver feature flags for local test tooling; the test gate must not mutate `Verify_CertInfo`, certificate parsing state, DynData parsing, Windows driver load policy, or per-SREV runtime behavior paths. |
| Topology | `Sandboxie.ini [GlobalSettings] Test=true -> Conf_Get(NULL, "Test", 0) -> MyIsTestMode -> MyIsCallerSigned / Process_Create / Api_QueryDriverInfo`. Windows driver image loading remains outside this topology because the driver must already be loadable before the setting can be evaluated. |
| Logic Risk | Reusing `Driver_OsTestSigning` as the sole local test signal conflates the Windows boot/code-integrity environment with Sandboxie's own test intent. A single explicit `Test=true` setting gives the local fork a direct and visible test gate without adding per-patch switches. |
| Fix | `util.c` now defines `MyIsTestMode`, which reads the global `Test` setting and accepts `true`, `yes`, `y`, `1`, and `on`. `MyIsCallerSigned` returns true under `Test=true`. `process.c` bypasses local supporter-certificate process gates under `Test=true`. `api.c` reports the corresponding feature flags under `Test=true`. No `Verify_CertInfo` state, certificate parser, DynData parser, Windows loader policy, or per-SREV runtime path changed. |
| Acceptance Gate | `docs/plan/local/check-ltest-001.py` validates the draft-07 schema, single helper predicate, accepted `Test=true` spellings, caller-signature bypass, process feature gates, driver feature flags, non-mutation of `Verify_CertInfo`, and local ledger entry; `docs/plan/local/check-ltest-001.sh` is the targeted wrapper. Windows gate: build the driver and run a Sandboxie.ini `Test=true` smoke proving unsigned local development caller APIs, process feature gates, and feature flags are locally bypassed while driver loading still uses the OS signing environment. |
