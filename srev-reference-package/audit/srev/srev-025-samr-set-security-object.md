# SREV-025: SAMR SetSecurityObject Trusted Sandboxie Image Gate

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> logic -> action |
| Input Artifact | `Ipc_Filter_Sam_Msg` SAMR opnum filter |
| Output Artifact | Source-level trusted-image exception for `SamrSetSecurityObject` |
| Owner | Driver IPC SAM endpoint policy |
| Acceptance Gate | `SamrSetSecurityObject` remains denied for ordinary sandboxed clients and is allowed only for Sandboxie-owned images. |

## Official Shape

Microsoft MS-SAMR documents `SamrSetSecurityObject` as opnum 2:

```text
https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/6666a066-58cf-4118-bf4b-dd54ed55ecf0
```

The operation sets access control on a SAM server, domain, user, group, or alias
object. MS-SAMR's object-based perspective also lists `SamrSetSecurityObject`
as an operation available across those object types:

```text
https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/8aaff2f7-1edd-41a0-ab58-4807ac6124c5
```

This is a security-descriptor update operation, not a read-only query.

## Local Shape

Sandboxie filters SAM RPC messages at the `\RPC Control\samss lpc` endpoint
before the request reaches SAM. The local filter blocks mutating SAM methods and
allows query/open methods.

The source comment on opnum 2 said `SandboxieCrypto.exe` sometimes needs
`SamSetSecurityObject` and suggested an `image_sbie` exception. `proc->image_sbie`
is set only when the process image path is under the Sandboxie install directory.

## Finding

Blocking opnum 2 for every caller is stricter than the compatibility need
recorded by the source comment. Allowing opnum 2 for every sandboxed caller
would be too broad because the official operation mutates SAM object security.

## Fix

`SamrSetSecurityObject` is now allowed only when `proc->image_sbie` is true.
All ordinary sandboxed callers still fall through to the mutating-SAM deny list.

## Runtime Gate

Windows runtime proof:

1. `SandboxieCrypto.exe` can complete the SAM operation that previously needed
   opnum 2;
2. a non-Sandboxie sandboxed process is still denied on opnum 2;
3. existing blocked SAM mutation opnums remain denied;
4. read/query SAM opnums remain unaffected.
