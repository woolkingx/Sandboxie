# SREV-157: DriverAssist Sandboxie SID Account Name Bounds

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/svc/DriverAssist.h and Sandboxie/core/svc/DriverAssistSid.cpp
output artifact: bounded account-name construction plus virtual-SID status gate
owner: Sandboxie/core/svc/DriverAssistSid.cpp
acceptance gate: docs/plan/check-srev-157.py and docs/plan/check-srev-157.sh
```

## Data

`Sandboxie/core/svc/DriverAssist.h` declares `DriverAssist::GetSandboxieSID`.
`Sandboxie/core/svc/DriverAssistSid.cpp` owns the implementation that maps a
sandbox box name to a `Sandboxie\BoxName` account lookup, falls back to a
virtual-account SID, and registers the name mapping with LSA.

Before this SREV, the account name was built in `WCHAR szUserName[256]` with
`wcscpy(szUserName, SANDBOXIE)`, then unbounded `wcscat` calls for `"\\"` and
the caller-supplied `boxname`. The fallback path also ignored the `NTSTATUS`
returned by `RtlCreateVirtualAccountSid` before passing the output SID buffer to
`AddSidName`.

## Official Shape

- Microsoft documents `LookupAccountNameW` as accepting a null-terminated
  `lpAccountName` string and recommends fully qualified `domain_name\user_name`
  form for unambiguous lookup:
  `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountnamew`.
- Microsoft documents `StringCchPrintfW` as receiving a destination buffer and
  its size in characters, preventing writes past the destination and returning
  an `HRESULT` that should be checked with `SUCCEEDED` / `FAILED`:
  `https://learn.microsoft.com/en-us/windows/win32/api/strsafe/nf-strsafe-stringcchprintfw`.
- Microsoft documents `RtlInitUnicodeString` as initializing a
  `UNICODE_STRING` from an optional source string:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring`.
- Microsoft-generated Windows metadata exposes `RtlCreateVirtualAccountSid` as
  taking `UNICODE_STRING`, base subauthority, output SID, in/out SID length, and
  returning `NTSTATUS`:
  `https://microsoft.github.io/windows-docs-rs/doc/windows/Wdk/Storage/FileSystem/fn.RtlCreateVirtualAccountSid.html`.

## Schema

`DRIVERASSIST_SANDBOXIE_SID_ACCOUNT_NAME_BOUNDS` says:

- `DriverAssist::GetSandboxieSID` owns the service-side Sandboxie account-name
  string passed to `LookupAccountNameW`.
- `LookupAccountNameW` receives a null-terminated account string in either
  `Sandboxie` or `Sandboxie\BoxName` form.
- The fixed `szUserName` buffer must be populated by a bounded API that knows
  `ARRAYSIZE(szUserName)`.
- Truncated or otherwise failed account-name formatting is a local failure and
  must not proceed to account lookup or virtual SID registration.
- The virtual SID fallback must not pass `pSID` to `AddSidName` unless
  `RtlCreateVirtualAccountSid` returned success.
- This SREV does not change `SandboxieLogon` policy, domain name selection,
  `LookupAccountNameW` SID/domain buffer ownership, or LSA mapping semantics.

## Topology

Legal flow:

```text
boxname -> SandboxieLogon config gate
        -> bounded Sandboxie or Sandboxie\BoxName account string
        -> LookupAccountNameW local-system account lookup
        -> if found: caller SID buffer owns result
        -> if not found: RtlInitUnicodeString(boxname or Sandboxie)
        -> RtlCreateVirtualAccountSid success gate
        -> AddSidName(Sandboxie domain, optional box user)
```

The owner boundary is the account-name string and SID buffer handoff inside
`DriverAssist::GetSandboxieSID`. `LookupAccountNameW` and
`RtlCreateVirtualAccountSid` are external Windows APIs; their return values are
the only legal proof that the output buffers contain usable SID data.

## Logic Risk

The old unbounded `wcscat` path let a long box name cross from configuration
data into a fixed stack buffer before the Windows account lookup boundary. The
fallback then ignored the virtual-SID creation status, so failure could still
flow into LSA name mapping with an unproven SID buffer. The correct local repair
is to make account-name formatting bounded and to fail closed before the LSA
mapping edge when virtual-SID creation fails.

## Fix

`DriverAssist::GetSandboxieSID` now builds `szUserName` with
`StringCchPrintfW(..., ARRAYSIZE(szUserName), ...)` and returns `false` on a
failed formatting result. It stores the `RtlCreateVirtualAccountSid` return
value and returns `false` unless that `NTSTATUS` indicates success. No
SandboxieLogon policy, lookup scope, domain string, LSA add/remove mapping
shape, or caller SID storage size changed.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-157.py
bash docs/plan/check-srev-157.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-157.py &&
bash docs/plan/check-srev-157.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows service build for `DriverAssistSid.cpp`, a
SandboxieLogon-enabled box whose name approaches the 256-character account-name
buffer limit proving long names fail closed without corrupting stack state, a
normal SandboxieLogon-enabled box proving `LookupAccountNameW` / virtual SID
creation still succeeds, and LSA mapping smoke proving the registered
`Sandboxie\BoxName` still resolves.
