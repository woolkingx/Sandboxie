# SREV-255: Credential ANSI Todo Boundary Comment

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/cred.c`, SREV-245, Microsoft WinCred ANSI array references |
| Output artifact | `docs/plan/srev-255-cred-ansi-todo-boundary-comment.schema.json`, `docs/plan/check-srev-255.py`, `docs/plan/check-srev-255.sh`, ledger fragment, comment-only source clarification |
| Owner | `Cred_CredReadDomainCredentialsA` and `Cred_CredEnumerateA` documented passthrough boundary |
| Acceptance gate | targeted source checker plus SREV-245 adjacency checker, core coverage, and diff checkpoint |

## Evidence

SREV-245 already records the real behavior gap: the ANSI credential-array APIs
call the native `CredReadDomainCredentialsA` / `CredEnumerateA` paths directly,
while the W siblings inspect and merge Sandboxie's PStore-backed credential
namespace.

The source still carried two bare `// todo` comments at that boundary. A bare
todo does not name the legal output shape, the owner of the future conversion,
or the reason this path must not simply call W and return W-owned data through
an ANSI API.

Official references are inherited from SREV-245:

- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credenumeratea
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreaddomaincredentialsa
- https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credfree

## Data

`Cred_CredReadDomainCredentialsA`, `Cred_CredEnumerateA`,
`__sys_CredReadDomainCredentialsA`, `__sys_CredEnumerateA`, `PCREDENTIALA **`,
`CredFree`, and SREV-245's ANSI credential-array conversion contract.

## Schema

`CRED_ANSI_TODO_BOUNDARY_COMMENT` says:

- the current ANSI array APIs remain direct native passthroughs;
- the source comments must point to SREV-245 as the owner of the unfinished
  virtualization boundary;
- future behavior change requires a `CredFree`-compatible ANSI array conversion
  owner;
- this SREV must not change hook registration, native passthrough calls,
  credential conversion helpers, PStore merge behavior, or WinCred flags.

## Topology

```text
CredReadDomainCredentialsA / CredEnumerateA
  -> documented SREV-245 boundary comment
  -> native Advapi credential API passthrough
```

Future topology remains the one named by SREV-245:

```text
ANSI input conversion
  -> W local owner path
  -> W result array
  -> ANSI single-block array conversion
  -> caller frees with CredFree-compatible free path
```

## Logic Risk

The dangerous failure mode is not merely "todo remains"; it is a future patch
that sees the W path and returns W-owned data through the ANSI API, or returns
several separately allocated ANSI credential blocks behind one `PCREDENTIALA **`
array. That would violate the official free/ownership shape.

## Fix

Comment-only source clarification. The two bare todo comments now state that
ANSI array virtualization is owned by SREV-245 and that native passthrough stays
until a `CredFree`-compatible ANSI array conversion owner exists. No behavior
changed.

## Acceptance Gate

`docs/plan/check-srev-255.py` validates the draft-07 schema, SREV-245 adjacency,
source comments, removal of the bare todo comments from the two ANSI functions,
native passthrough preservation, and the ledger fragment.

Runtime gate: inherited from SREV-245. Windows credential smoke is still needed
before claiming ANSI local credential visibility or returned-array ownership is
fixed.
