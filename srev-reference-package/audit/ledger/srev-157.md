---
kind: srev-ledger-entry
id: SREV-157
title: DriverAssist Sandboxie SID Account Name Bounds
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/svc/DriverAssistSid.cpp
spec: docs/plan/srev-157-driverassist-sandboxie-sid-account-name-bounds.md
schema: docs/plan/srev-157-driverassist-sandboxie-sid-account-name-bounds.schema.json
checker: docs/plan/check-srev-157.py
runtime_gate: "Windows service build for `DriverAssistSid.cpp`, long SandboxieLogon box-name fail-closed smoke, normal SandboxieLogon SID lookup/virtual SID fallback smoke, and LSA mapping resolution smoke"
---

### SREV-157: DriverAssist Sandboxie SID Account Name Bounds

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `LookupAccountNameW`, `StringCchPrintfW`, `RtlInitUnicodeString`, and `RtlCreateVirtualAccountSid` shape review; needs Windows service/runtime proof |
| Evidence | `Sandboxie/core/svc/DriverAssist.h` was the highest-ranked unnamed reviewable core file after SREV-156. Its `DriverAssist::GetSandboxieSID` declaration is implemented in `Sandboxie/core/svc/DriverAssistSid.cpp`, which builds a `Sandboxie` or `Sandboxie\BoxName` account string, calls `LookupAccountName`, falls back to `RtlCreateVirtualAccountSid`, and registers the mapping with `AddSidName`. Before this SREV, `szUserName[256]` was populated with unbounded `wcscpy` / `wcscat` from `boxname`, and the fallback ignored the `NTSTATUS` from `RtlCreateVirtualAccountSid` before passing `pSID` to `AddSidName`. Microsoft documents `LookupAccountNameW` as receiving a null-terminated account string and recommending fully qualified `domain_name\user_name` form; documents `StringCchPrintfW` as receiving a destination buffer plus size in characters and returning `HRESULT`; documents `RtlInitUnicodeString` as initializing a counted `UNICODE_STRING`; and Microsoft-generated Windows metadata exposes `RtlCreateVirtualAccountSid` as returning `NTSTATUS`. |
| Data | `Sandboxie/core/svc/DriverAssist.h`, `Sandboxie/core/svc/DriverAssistSid.cpp`, `DriverAssist::GetSandboxieSID`, `boxname`, `SandboxieLogon`, `szUserName[256]`, `szDomainName[256]`, `LookupAccountNameW`, `SID_NAME_USE`, `RtlInitUnicodeString`, `RtlCreateVirtualAccountSid`, `AddSidName`, `SANDBOXIE`, `SBIE_RID`, `pSID`, and `dwSidSize`. |
| Schema | `DRIVERASSIST_SANDBOXIE_SID_ACCOUNT_NAME_BOUNDS` says `DriverAssist::GetSandboxieSID` owns the service-side account string passed to `LookupAccountNameW`; `LookupAccountNameW` receives a null-terminated account string in `Sandboxie` or `Sandboxie\BoxName` form; `szUserName` must be populated by a bounded API using `ARRAYSIZE(szUserName)`; failed or truncated formatting returns `false` before account lookup; `RtlCreateVirtualAccountSid` must return success before `AddSidName` receives `pSID`; and this SREV does not change `SandboxieLogon` policy, `LookupAccountNameW` scope, domain string, or LSA mapping semantics. |
| Topology | Legal flow is `boxname`, `SandboxieLogon` config gate, bounded `Sandboxie` / `Sandboxie\BoxName` account-name construction, `LookupAccountNameW`, caller-owned SID buffer return on success, `RtlInitUnicodeString`, `RtlCreateVirtualAccountSid` success gate, and `AddSidName(SANDBOXIE, boxname)`. |
| Logic Risk | A long box name was configuration data crossing into a fixed stack buffer before the Windows account lookup boundary. The ignored virtual-SID status meant a failed SID creation could still flow into LSA name mapping with an unproven SID buffer. This is a local owner-boundary defect, not a reason to change the SandboxieLogon policy or LSA naming model. |
| Official Shape | `docs/plan/srev-157-driverassist-sandboxie-sid-account-name-bounds.md` records Microsoft `LookupAccountNameW`, `StringCchPrintfW`, `RtlInitUnicodeString`, and `RtlCreateVirtualAccountSid` references. `docs/plan/srev-157-driverassist-sandboxie-sid-account-name-bounds.schema.json` records the JSON Schema draft-07 local `DRIVERASSIST_SANDBOXIE_SID_ACCOUNT_NAME_BOUNDS` contract. |
| Fix | `DriverAssist::GetSandboxieSID` now builds `szUserName` with `StringCchPrintfW(..., ARRAYSIZE(szUserName), ...)` and returns `false` if formatting fails. The fallback now stores `RtlCreateVirtualAccountSid` status and returns `false` before `AddSidName` unless virtual SID creation succeeds. No `SandboxieLogon` query, lookup scope, domain name, LSA add/remove operation, or caller SID buffer size changed. |
| Acceptance Gate | `docs/plan/check-srev-157.py` validates the draft-07 schema, official references, `DriverAssist.h` declaration ownership, bounded account-name formatting, fail-closed formatting gate before `LookupAccountNameW`, virtual-SID status gate before `AddSidName`, stale unbounded `wcscpy` / `wcscat` removal, and ledger entry; `docs/plan/check-srev-157.sh` is the matrix wrapper. Runtime/build gate: Windows service build for `DriverAssistSid.cpp`, long SandboxieLogon box-name fail-closed smoke, normal SandboxieLogon SID lookup/virtual SID fallback smoke, and LSA mapping resolution smoke. |
