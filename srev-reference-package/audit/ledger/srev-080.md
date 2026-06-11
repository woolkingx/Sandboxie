---
kind: srev-ledger-entry
id: SREV-080
title: UserEnv VerifyVersionInfo Override Contract
status: patched-source-level-after-official-verifyversioninfow-versetconditionmask-shape
owner: Sandboxie/core/dll/userenv.c
spec: docs/plan/srev-080-userenv-verify-version-info.md
schema: docs/plan/srev-080-userenv-verify-version-info.schema.json
checker: docs/plan/check-srev-080.py
runtime_gate: "`OverrideOsBuild` plus `VerifyVersionInfoW` / `VersionHelpers.h` major/minor/service-pack/build checks match `RtlGetVersion` / `GetVersionEx*`, while platform/product/suite checks stay tied to the real system"
---
### SREV-080: UserEnv VerifyVersionInfo Override Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `VerifyVersionInfoW` / `VerSetConditionMask` shape and local `OverrideOsBuild` topology analysis; needs Windows version-helper runtime proof |
| Evidence | `Sandboxie/core/dll/userenv.c` implements `OverrideOsBuild` through `RtlGetVersion`, `GetVersionExW`, and `GetVersionExA`, but the same file still had a TODO to hook the version-verification path. Microsoft documents `VerifyVersionInfoW` as the public API for testing caller-supplied `OSVERSIONINFOEXW` requirements, with `dwTypeMask` selecting members and `dwlConditionMask` built by `VerSetConditionMask`. Version helper APIs are documented as wrappers over `VerifyVersionInfo`. |
| Data | `OverrideOsBuild`, synthetic major/minor/build/service-pack fields, real platform/product/suite fields, caller `OSVERSIONINFOEXW`, `dwTypeMask`, `dwlConditionMask`, boolean result, and `GetLastError` projection. |
| Schema | `USERENV_VERIFY_VERSION_INFO_OVERRIDE` says documented `VerifyVersionInfoW` is the public boundary; condition decoding goes through `VerSetConditionMask`; `OverrideOsBuild` changes only major/minor/build/service-pack fields; platform/product/suite remain real system fields; mismatch returns `ERROR_OLD_WIN_VERSION`; invalid input/mask/condition returns `ERROR_INVALID_PARAMETER`. |
| Topology | Caller `VerifyVersionInfoW` now crosses into `UserEnv_VerifyVersionInfoW`; the hook gets real OS fields through `__sys_RtlGetVersion`, applies the existing `UserEnv_MkVersionEx` override tuple, decodes requested comparison operators with `VerSetConditionMask`, then returns the documented boolean/error projection. |
| Logic Risk | Without this hook, a process can see two incompatible version truths: `GetVersionEx*` / `RtlGetVersion` report the overridden build, while `VerifyVersionInfoW` and `VersionHelpers.h` checks report the host build. The old TODO named private `RtlSwitchedVVI`, but the stable boundary to implement is documented `VerifyVersionInfoW`. |
| Official Shape | `docs/plan/srev-080-userenv-verify-version-info.md` records Microsoft `VerifyVersionInfoW`, `VerSetConditionMask`, version helper, and `RtlVerifyVersionInfo` references. `docs/plan/srev-080-userenv-verify-version-info.schema.json` records the JSON Schema draft-07 local `USERENV_VERIFY_VERSION_INFO_OVERRIDE` contract. |
| Fix | `UserEnv_InitVer` now hooks `VerifyVersionInfoW` when present and loads `VerSetConditionMask`. `UserEnv_VerifyVersionInfoW` evaluates caller requirements against the same `OverrideOsBuild` tuple used by existing version hooks, preserving real platform/product/suite fields and splitting `ERROR_OLD_WIN_VERSION` from `ERROR_INVALID_PARAMETER`. |
| Acceptance Gate | `docs/plan/check-srev-080.py` validates the draft-07 schema, official references, public API hook, `VerSetConditionMask`-based condition decoding, private TODO removal, override-field projection, error split, and ledger entry; `docs/plan/check-srev-080.sh` is the matrix wrapper. Windows gate: `OverrideOsBuild` plus `VerifyVersionInfoW` / `VersionHelpers.h` major/minor/service-pack/build checks match `RtlGetVersion` / `GetVersionEx*`, while platform/product/suite checks stay tied to the real system. |
