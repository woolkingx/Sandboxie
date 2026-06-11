---
kind: srev-ledger-entry
id: SREV-118
title: IPC LSA Counted Port Name
status: patched-source-level-after-official-object-name-information-unicode-string-and-r
owner: Sandboxie/core/drv/ipc_lsa.c
spec: docs/plan/srev-118-ipc-lsa-counted-port-name.md
schema: docs/plan/srev-118-ipc-lsa-counted-port-name.schema.json
checker: docs/plan/check-srev-118.py
runtime_gate: "Windows driver build for `ipc_lsa.c`, object-name instrumentation proving counted endpoint matching works without a trailing NUL, normal LSA authentication-port and LSARPC endpoint traffic, and unchanged KPATH-004/KPATH-006 runtime gates"
---
### SREV-118: IPC LSA Counted Port Name

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `OBJECT_NAME_INFORMATION` / `UNICODE_STRING` and `RtlEqualUnicodeString` shape; needs Windows driver build/object-name runtime proof |
| Evidence | `Sandboxie/core/drv/ipc_lsa.c` was the highest-ranked unnamed reviewable core file after SREV-117. `Ipc_CheckPortRequest_Lsa` and `Ipc_CheckPortRequest_LsaEP` receive an `OBJECT_NAME_INFORMATION *Name`, check `Name->Name.Length`, then compared `Name->Name.Buffer` to literal LSA endpoint names with `_wcsicmp`. Microsoft documents `OBJECT_NAME_INFORMATION` as containing `UNICODE_STRING Name`; `UNICODE_STRING.Length` is a byte count and does not include a terminating NUL if present. Therefore length checks alone do not make `Name->Name.Buffer` safe for C-string scanning. |
| Data | `Ipc_CheckPortRequest_Lsa`, `Ipc_CheckPortRequest_LsaEP`, `Ipc_Lsa_MatchPortName`, `OBJECT_NAME_INFORMATION.Name`, `UNICODE_STRING.Length`, `UNICODE_STRING.Buffer`, `RtlInitUnicodeString`, `RtlEqualUnicodeString`, `\LsaAuthenticationPort`, `\RPC Control\lsasspirpc`, `\RPC Control\LSARPC_ENDPOINT`, KPATH-004 LSAD opnum policy, and KPATH-006 RPC payload capture. |
| Schema | `IPC_LSA_COUNTED_PORT_NAME` says `OBJECT_NAME_INFORMATION.Name` is a counted `UNICODE_STRING`; `UNICODE_STRING.Length` is a byte count and does not prove `Buffer` is NUL-terminated; LSA endpoint matching must compare counted strings, not C-string scans over `Name->Name.Buffer`; `Ipc_CheckPortRequest_Lsa` continues to accept only `\LsaAuthenticationPort` and `\RPC Control\lsasspirpc` when `ipc_block_password` is enabled; `Ipc_CheckPortRequest_LsaEP` continues to accept only `\RPC Control\LSARPC_ENDPOINT` unless `OpenLsaEndpoint` is enabled; this SREV does not change MS-LSAD opnum policy, password-change detection, KPATH-004 secret/private-data denial, KPATH-006 RPC payload capture, or `OpenLsaEndpoint` behavior. |
| Topology | Object manager name data flows as `OBJECT_NAME_INFORMATION.Name { Length, MaximumLength, Buffer }` into `ipc_lsa.c` port-name gates. `Ipc_Lsa_MatchPortName` initializes the expected literal with `RtlInitUnicodeString`, then compares counted strings using `RtlEqualUnicodeString(..., TRUE)`. Only after the object-name boundary matches does the LSA authentication-port password filter or LSARPC endpoint opnum filter run. |
| Logic Risk | `_wcsicmp` searches for a terminating NUL and may read past the counted object-name buffer. In an endpoint filter, that turns a simple name gate into an out-of-bounds read before the LSARPC policy code even runs. The fix is independent from KPATH-004 and KPATH-006: those gates still own opnum semantics and RPC payload parsing, while this SREV owns the earlier object-name data shape. |
| Official Shape | `docs/plan/srev-118-ipc-lsa-counted-port-name.md` records Microsoft `ObQueryNameString` / `OBJECT_NAME_INFORMATION`, `UNICODE_STRING`, `RtlEqualUnicodeString`, and `RtlInitUnicodeString` references. `docs/plan/srev-118-ipc-lsa-counted-port-name.schema.json` records the JSON Schema draft-07 local `IPC_LSA_COUNTED_PORT_NAME` contract. |
| Fix | `ipc_lsa.c` now has `Ipc_Lsa_MatchPortName`, which compares `Name->Name` to endpoint literals as counted Unicode strings. The three LSA endpoint gates no longer call `_wcsicmp(Name->Name.Buffer, ...)`. No LSARPC opnum allow/deny decision, RPC message-id extraction, trace capture, password-change scan, event-log message, `OpenLsaEndpoint` escape hatch, or Windows-version branch changed. |
| Acceptance Gate | `docs/plan/check-srev-118.py` validates the draft-07 schema, official references, counted `UNICODE_STRING` endpoint helper, removal of `_wcsicmp(Name->Name.Buffer, ...)` from `ipc_lsa.c`, preservation of KPATH-004 secret/private-data opnum cases, preservation of KPATH-006 `Ipc_GetRpcMsgId` routing, and ledger entry; `docs/plan/check-srev-118.sh` is the matrix wrapper. Runtime/build gate: Windows driver build for `ipc_lsa.c`, object-name instrumentation proving counted endpoint matching works without a trailing NUL, normal LSA authentication-port and LSARPC endpoint traffic, and unchanged KPATH-004/KPATH-006 runtime gates. |
