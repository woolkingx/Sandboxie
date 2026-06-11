# SREV-080: UserEnv VerifyVersionInfo Override Contract

## Data

`Sandboxie/core/dll/userenv.c` implements the `OverrideOsBuild` compatibility
setting by hooking `RtlGetVersion`, `GetVersionExW`, and `GetVersionExA`.
The file also carried a TODO to hook the version-verification path.

The relevant data nodes are:

```text
OverrideOsBuild setting
synthetic OSVERSIONINFOEXW version tuple
VerifyVersionInfoW input requirement structure
dwTypeMask member selection
dwlConditionMask comparison operators
boolean version-match result
GetLastError failure projection
```

## Official Shape

Microsoft documents `VerifyVersionInfoW` as comparing caller-supplied
`OSVERSIONINFOEXW` requirements against the running OS. `dwTypeMask` selects
members, `dwlConditionMask` supplies the comparison operator, success returns
nonzero, mismatch returns zero with `ERROR_OLD_WIN_VERSION`, and other failures
return zero with another error.

Microsoft documents `VerSetConditionMask` as the official builder for
`dwlConditionMask`; callers initialize the mask to zero and call it once for
each member selected by `dwTypeMask`.

Microsoft documents version helper APIs as wrappers over `VerifyVersionInfo`
using greater-than-or-equal tests.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-verifyversioninfow
https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-versetconditionmask
https://learn.microsoft.com/en-us/windows/win32/sysinfo/version-helper-apis
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlverifyversioninfo
```

## Schema

Local schema:

```text
docs/plan/srev-080-userenv-verify-version-info.schema.json
```

The override contract is:

```text
documented VerifyVersionInfoW is the public boundary, not private RtlSwitchedVVI
condition-mask decoding must go through VerSetConditionMask, not hardcoded bit layout
OverrideOsBuild changes only major, minor, build, and service-pack fields
platform, product type, and suite comparisons keep the real system fields
version mismatch returns ERROR_OLD_WIN_VERSION
invalid mask/condition/input shape returns ERROR_INVALID_PARAMETER
```

## Topology

```text
caller VerifyVersionInfoW
  -> Sandboxie UserEnv_VerifyVersionInfoW hook
  -> real RtlGetVersion for non-overridden fields
  -> UserEnv_MkVersionEx for OverrideOsBuild tuple
  -> VerSetConditionMask-based condition decoding
  -> documented success / GetLastError projection
```

The hook owner is `userenv.c`, the same owner that already projects
`OverrideOsBuild` through `RtlGetVersion` and `GetVersionEx*`.

## Logic Risk

Before this patch, code using `VerifyVersionInfoW` or `VersionHelpers.h` could
observe the host OS version while adjacent calls to `GetVersionEx*` observed the
Sandboxie override. That splits one compatibility setting into two version
truths and makes routing depend on which API a program chooses.

The old TODO named `RtlSwitchedVVI`, but that is an internal implementation
detail. The stable public shape is the documented `VerifyVersionInfoW` API.

## Fix

`UserEnv_InitVer` now hooks `VerifyVersionInfoW` when the export exists, and
loads `VerSetConditionMask` from the same module or `kernel32.dll`.

`UserEnv_VerifyVersionInfoW` now builds a current `OSVERSIONINFOEXW` from the
real system fields, applies `OverrideOsBuild` to the same fields already owned
by `UserEnv_MkVersionEx`, decodes each requested condition by round-tripping
through `VerSetConditionMask`, and returns the documented mismatch or invalid
parameter errors.

## Acceptance Gate

`docs/plan/check-srev-080.py` validates the draft-07 schema, official
references, public `VerifyVersionInfoW` hook, `VerSetConditionMask`-based
condition decoding, removal of the private `RtlSwitchedVVI` TODO, override-field
projection, invalid-parameter split, mismatch split, and ledger entry.

Windows gate: with `OverrideOsBuild` enabled, `VerifyVersionInfoW` and
`VersionHelpers.h` checks for major/minor/service-pack/build requirements should
match the same synthetic version tuple as `RtlGetVersion` / `GetVersionEx*`;
platform/product/suite checks should continue to reflect the real system.
