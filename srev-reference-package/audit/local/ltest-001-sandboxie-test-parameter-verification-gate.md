# LTEST-001: Sandboxie Test Parameter Verification Gate

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> boundary -> action -> verify |
| Input artifact | `Sandboxie/core/drv/util.c`, `Sandboxie/core/drv/process.c`, `Sandboxie/core/drv/api.c`, local Sandboxie config, and the existing `MyIsCallerSigned` / `Verify_CertInfo` gates |
| Output artifact | One global `Test=true` local test gate for Sandboxie internal verification paths |
| Owner | `Sandboxie/core/drv/util.c` owns the `Test=true` predicate; `process.c` and `api.c` consume it only at Sandboxie internal certificate/feature gates |
| Acceptance gate | Source readback proves `Test=true` is parsed in one helper, bypasses caller signature checks, suppresses supporter-certificate process termination gates, and reports driver feature flags as available for local testing without changing Windows loader signing behavior |

## Data

- Global Sandboxie configuration setting: `Test=true`.
- Kernel helper: `MyIsTestMode`.
- Caller verification gate: `MyIsCallerSigned`.
- Supporter-certificate feature gates: `Verify_CertInfo.active`, `opt_sec`, `opt_enc`, `opt_net`, and `eCertDeveloper`.
- Driver feature flags returned by `Api_QueryDriverInfo`.

## Schema

`SANDBOXIE_TEST_PARAMETER_VERIFICATION_GATE`:

- `Test=true` is a local Sandboxie runtime setting, not a Windows loader signing control.
- The setting is parsed by a single kernel helper, `MyIsTestMode`.
- Accepted true spellings are `true`, `yes`, `y`, `1`, and `on`.
- `MyIsCallerSigned` must treat `Test=true` as a local development caller-signature bypass.
- Supporter-certificate process gates in `Process_Create` must treat `Test=true` as a local test pass for security/privacy/compartment and encryption options.
- Driver feature reporting must expose the same local test availability through `SBIE_FEATURE_FLAG_CERTIFIED`, `SBIE_FEATURE_FLAG_SECURITY_MODE`, `SBIE_FEATURE_FLAG_PRIVACY_MODE`, `SBIE_FEATURE_FLAG_COMPARTMENTS`, `SBIE_FEATURE_FLAG_ENCRYPTION`, `SBIE_FEATURE_FLAG_NET_PROXY`, and `SBIE_FEATURE_FLAG_NO_SIG`.
- This local test entry must not mutate `Verify_CertInfo`, certificate parsing, sidecar signature verification, DynData parsing, Windows driver load policy, or per-SREV runtime behavior paths.
- This entry is not an SREV and must not be included in the upstream-facing SREV/KPATH ledger.

## Topology

```text
Sandboxie.ini [GlobalSettings] Test=true
  -> driver Conf_Get(NULL, "Test", 0)
  -> MyIsTestMode()
  -> MyIsCallerSigned local bypass
  -> Process_Create local feature gate bypass
  -> Api_QueryDriverInfo local feature-flag projection
```

Windows driver image loading remains outside this topology. The driver must
already be loadable by Windows before this setting can be evaluated.

## Logic Risk

The previous shortcut was `Driver_OsTestSigning`, which is too broad: it says
something about the Windows boot/code-integrity environment, not about the local
Sandboxie test intent. `Test=true` makes the local test intent explicit and
keeps the bypass visible at Sandboxie's own verification gates.

## Fix

`util.c` now defines `MyIsTestMode`, which reads the global `Test` setting and
accepts `true`, `yes`, `y`, `1`, and `on` as enabled values. `MyIsCallerSigned`
returns true under `Test=true`, so unsigned local development callers can drive
the test build.

`process.c` treats `Test=true` as a local pass for supporter-certificate security
and encryption gates, avoiding test-only process termination while patched core
paths are exercised.

`api.c` projects `Test=true` into driver feature flags so user-mode tooling sees
the same local test availability.

## Acceptance Gate

`docs/plan/local/check-ltest-001.py` validates the draft-07 schema, single helper
predicate, accepted `Test=true` spellings, caller-signature bypass, process
feature gates, driver feature flags, non-mutation of `Verify_CertInfo`, and the
local ledger entry. Linux verification is source-level only; Windows build and runtime proof remain required.
