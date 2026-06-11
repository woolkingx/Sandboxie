# SREV-308: Key CreateProcess SRP Authenticode Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, Microsoft `ZwQueryValueKey` / `KEY_VALUE_PARTIAL_INFORMATION`, `CreateProcessW`, and Software Restriction Policies certificate-rule references |
| Output artifact | CreateProcess-time SRP Authenticode fake-value owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_NtQueryValueKeyFakeForCreateProcess` |
| Acceptance gate | Targeted checker validates source comment ownership, unchanged `TlsData->proc_create_process` dispatch, unchanged value predicate and payload shape, official references, SRP topology adjacency, combined ledger, and ledger fragment |

## Data

`Key_NtQueryValueKey` calls `Key_NtQueryValueKeyFakeForCreateProcess` only from
the `KeyValuePartialInformation` fake-value gate while
`TlsData->proc_create_process` is set:

```text
CreateProcess path
  -> TlsData->proc_create_process
  -> KeyValuePartialInformation registry query
  -> Key_NtQueryValueKeyFakeForCreateProcess
```

The fake owner currently fabricates exactly one DWORD value:

```text
AuthenticodeEnabled -> REG_DWORD 0
```

The old comment correctly named the symptom: when the SRP
`AuthenticodeEnabled` policy value is enabled during process creation, the
signature/certificate path can recurse into `SandboxieCrypto`, which can hang
while `SandboxieRpcSs` is loading. The comment did not name the public SRP
certificate-rule shape, the `CreateProcess` boundary, or the adjacent local SRP
mitigations.

## Official Shape

Microsoft documents `ZwQueryValueKey` as returning registry value information
into a caller-allocated buffer selected by `KeyValueInformationClass`, with
`Length` and `ResultLength` defining returned or required byte counts.

Microsoft documents `KEY_VALUE_PARTIAL_INFORMATION` as `TitleIndex`, `Type`,
`DataLength`, and inline `Data`.

Microsoft documents `CreateProcessW` as creating a new process and primary
thread in the calling process's security context, and says the function returns
before the new process finishes initialization.

Microsoft documents Software Restriction Policies as Group Policy-driven trust
policies that identify software and control whether it can run. The SRP
technical overview names Authenticode and WinVerifyTrust APIs as components used
to process signed executable files.

Microsoft documents the "Use certificate rules on Windows executables for
Software Restriction Policies" setting as determining whether digital
certificates are processed when SRP is enabled and a user or process attempts to
run an `.exe`. It says certificate rules allow/disallow Authenticode-signed
software and that enabling certificate rules makes SRP check CRLs when signed
programs start, which can affect startup performance.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwqueryvaluekey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_value_partial_information`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw`
- `https://learn.microsoft.com/en-us/windows-server/identity/software-restriction-policies/software-restriction-policies-technical-overview`
- `https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/security-policy-settings/system-settings-use-certificate-rules-on-windows-executables-for-software-restriction-policies`

## Schema

Local schema:

```text
docs/plan/srev-308-key-createprocess-srp-authenticode-owner.schema.json
```

Contract id:

```text
KEY_CREATEPROCESS_SRP_AUTHENTICODE_OWNER
```

## Topology

```text
CreateProcess
  -> Sandboxie process-create instrumentation sets TlsData->proc_create_process
  -> SRP certificate-rule registry query asks for AuthenticodeEnabled
  -> Key_NtQueryValueKeyFakeForCreateProcess
  -> synthetic REG_DWORD 0 KEY_VALUE_PARTIAL_INFORMATION
  -> avoid recursive SandboxieCrypto startup during SandboxieRpcSs loading
```

Adjacent local SRP/AppLocker mitigations:

```text
AdvApi_EnableDisableSRP
  -> SaferComputeTokenFromLevel hook can return NULL token for retry

Token_Restrict(... SANDBOX_INERT ...)
  -> driver-side restricted primary token inhibits SRP/AppLocker checks
```

Those adjacent mitigations are topology evidence only. SREV-308 owns only the
registry fake-value branch in `key.c`.

## Logic Risk

The old comment focused on the hang symptom. The stable boundary is narrower and
more useful:

```text
CreateProcess-time SRP certificate-rule query
  -> exact AuthenticodeEnabled value name
  -> complete REG_DWORD KeyValuePartialInformation payload
  -> otherwise fall through unchanged
```

This branch intentionally changes a process-creation policy value. Future
changes to the value predicate, path guard, payload, or `proc_create_process`
scope require Windows runtime proof for process creation under SRP/AppLocker and
SandboxieCrypto/SandboxieRpcSs startup.

## Fix

The source comment now names SREV-308, the CreateProcess-time SRP
certificate-rule boundary, Microsoft's Authenticode/CRL processing shape for
signed executable launch, and the local reason for keeping this exact fake value
disabled during Sandboxie process creation.

No behavior changed: the `TlsData->proc_create_process` dispatcher, exact
`AuthenticodeEnabled` counted value-name predicate, `REG_DWORD` type, DWORD zero
payload, `ResultLength` calculation, `STATUS_SUCCESS`, `STATUS_BAD_INITIAL_PC`,
and normal registry merge/query path are unchanged.
This is a comment-only source clarification, no behavior change.

## Acceptance Gate

`docs/plan/check-srev-308.py` validates the draft-07 schema, official
references, source comment owner, unchanged `TlsData->proc_create_process`
dispatch, unchanged `AuthenticodeEnabled` predicate, unchanged
`KEY_VALUE_PARTIAL_INFORMATION` payload construction, adjacent SRP/AppLocker
topology evidence, combined ledger entry, and split ledger fragment.

Runtime gate: Windows process-creation smoke with SRP/AppLocker certificate-rule
policy enabled, proving no SandboxieCrypto/SandboxieRpcSs recursive hang and
showing unrelated registry value names fall through to normal merge/query
handling before any predicate change.
