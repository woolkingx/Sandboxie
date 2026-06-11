# SREV-245: Credential ANSI Enumeration And Domain Read Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/cred.c`, `Sandboxie/core/dll/advapi.h`, Microsoft WinCred references, SREV-034, SREV-116 |
| Output artifact | `docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.schema.json`, `docs/plan/check-srev-245.py`, `docs/plan/check-srev-245.sh`, ledger fragment |
| Owner | `cred.c` ANSI credential enumeration and domain-read hooks |
| Acceptance gate | source checker proves the current boundary gap and preserves the future patch contract; Windows credential runtime proof remains required before behavior closure |

## Evidence

`cred.c` used to have two local `// todo` comments on the ANSI
read/enumeration side. Those comments now point at this SREV's owner boundary:
ANSI array virtualization is not implemented until a `CredFree`-compatible
ANSI array conversion owner exists.

- `Cred_CredReadDomainCredentialsA` logs `CredReadDomainCredentialsA` and calls `__sys_CredReadDomainCredentialsA` directly.
- `Cred_CredEnumerateA` calls `__sys_CredEnumerateA` directly.

The wide-character siblings are not direct passthroughs. `Cred_CredReadDomainCredentialsW`
searches Sandboxie's local PStore-backed credential namespace first and falls
back to `__sys_CredReadDomainCredentialsW` only when no local domain credential
matches. `Cred_CredEnumerateW` enumerates local `SimpleCred-` items, merges them
with native `__sys_CredEnumerateW` results, and returns one credential-array
block.

Existing SREV coverage is adjacent but not the same owner:

- SREV-034 fixes single `CREDENTIALA` / `CREDENTIALW` conversion block
  ownership.
- SREV-116 fixes Advapi/Cred hook typedef pointer-depth for output slots.

Neither SREV defines how an ANSI array return from `CredEnumerateA` or
`CredReadDomainCredentialsA` should merge local PStore entries with native
credentials while preserving the official `PCREDENTIALA **` return shape.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credenumeratea
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credenumeratew
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreaddomaincredentialsa
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreaddomaincredentialsw
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credfree

## Data

`Cred_CredReadDomainCredentialsA`, `Cred_CredReadDomainCredentialsW`,
`Cred_CredEnumerateA`, `Cred_CredEnumerateW`, `Cred_CREDENTIAL_TARGET_INFORMATIONA2W`,
`Cred_CREDENTIALW2A`, `Cred_UnserializeN`, `Cred_SimpleCred`,
`Cred_DomainCred`, `__sys_CredReadDomainCredentialsA/W`,
`__sys_CredEnumerateA/W`, `PCREDENTIALA **`, `PCREDENTIALW **`, `CredFree`,
and Sandboxie's PStore-backed credential items.

## Schema

`CRED_ANSI_ENUM_DOMAIN_BOUNDARY` says:

- `cred.c` owns local credential virtualization before a credential enumerate or
  domain-read result leaves the sandboxed process.
- `CredEnumerateA` and `CredReadDomainCredentialsA` return ANSI credential-array
  output slots, not opaque native passthrough buffers.
- The official ANSI result is an array of `PCREDENTIALA` pointers in one
  allocated return block that the caller frees with `CredFree`.
- A future source patch must convert ANSI inputs to the wide local owner path,
  merge local PStore and native results through the same policy as the W path,
  and return a valid ANSI single-block result.
- A future patch must not return `PCREDENTIALW **` data through an ANSI API and
  must not return several separately allocated `CREDENTIALA` blocks as if they
  were one CredFree-owned block.
- Until that array conversion owner exists, the current direct ANSI passthrough
  remains a documented boundary gap, not a safe completed behavior.

## Topology

Current W topology:

```text
CredWriteA/W or CredWriteDomainCredentialsA/W
  -> converted W credential
  -> Sandboxie PStore namespace
  -> CredReadDomainCredentialsW / CredEnumerateW
      -> local PStore result
      -> native W fallback or merge
      -> W credential-array block
```

Current A topology:

```text
CredReadDomainCredentialsA / CredEnumerateA
  -> __sys_CredReadDomainCredentialsA / __sys_CredEnumerateA
  -> native credential set only
```

Required future topology:

```text
CredReadDomainCredentialsA / CredEnumerateA
  -> ANSI input conversion
  -> W local owner path
  -> W result array
  -> ANSI single-block array conversion
  -> caller frees with CredFree-compatible free path
```

## Logic Risk

The direct ANSI passthrough means an ANSI caller can miss credentials written
through Sandboxie's local credential virtualization, even though the W path sees
them. This is a semantic split at the credential boundary. The risky temptation
is to "just call W" and return the W array through the A API, or to convert each
credential into separate A blocks and return an array that does not match the
official single-block ownership contract.

This SREV therefore records the gap and the legal shape for a future patch
instead of making a partial behavior change.

## Fix

No source patch in this SREV. The current source remains documented as an open
boundary gap. A future patch needs a dedicated ANSI credential-array conversion
helper with an explicit size/count contract before changing
`Cred_CredReadDomainCredentialsA` or `Cred_CredEnumerateA`.

## Acceptance Gate

`docs/plan/check-srev-245.py` validates the draft-07 schema, official WinCred
references, current source evidence for the two ANSI direct passthroughs and
their SREV-245 owner-boundary comments, the W-path local PStore merge/fallback
topology, SREV-034/SREV-116 adjacency, and the split ledger fragment.

Runtime/build gate: Windows credential smoke where sandboxed `CredWriteA` /
`CredWriteDomainCredentialsA` entries are visible through `CredEnumerateA` /
`CredReadDomainCredentialsA`, native host credentials still merge according to
the intended policy, and returned ANSI arrays can be released by the expected
credential free path without leaks or invalid pointer graphs.
