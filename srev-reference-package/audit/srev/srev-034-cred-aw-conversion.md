# SREV-034: Credential A/W Conversion Block Ownership

## Finding

`Sandboxie/core/dll/cred.c` converts between `CREDENTIALA` and `CREDENTIALW`
when implementing the ANSI credential APIs over the internal wide-character
credential store.

`Cred_CREDENTIALW2A` allocated a `CREDENTIALA` output block, but initialized the
string cursor from the input `credW` block:

```c
char* ptr = ((char*)credW) + sizeof(CREDENTIALW);
```

`Cred_CopyW2A` also typed the output cursor as `WCHAR *`, so ANSI string writes
used wide-character stores while advancing the byte cursor as if each character
were one byte. Both are output-owner violations.

The attribute array cursor advanced by `sizeof(PCREDENTIAL_ATTRIBUTE*)`, a
pointer size, instead of `sizeof(CREDENTIAL_ATTRIBUTE*)`, the actual array
element size.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentiala`
- `https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritea`
- `https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreada`
- `https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credfree`

Relevant contract:

- `CREDENTIALA` / `CREDENTIALW` are pointer-bearing structures.
- `CredReadA` returns a single allocated block where contained pointers point
  inside that block.
- The returned credential buffer must be released by the credential API's free
  routine.
- `CredWriteA` receives a caller-owned `PCREDENTIALA`; the shim must not mutate
  the caller's structure while building its converted copy.

## Local Schema

Small machine-readable schema:

```text
docs/plan/srev-034-cred-aw-conversion.schema.json
```

Conversion output:

```text
LocalAlloc block
converted structure header
converted attribute array
converted strings
```

`CredentialBlob` and attribute `Value` payload pointers keep existing source
ownership in this local shim; this change only fixes the structure/string block
layout.

## Source Change

Credential conversion now:

- writes ANSI strings through a `char *` output cursor;
- starts `Cred_CREDENTIALW2A` cursor inside the `credA` output block;
- advances attribute arrays by `sizeof(CREDENTIAL_ATTRIBUTEA/W)`;
- checks `LocalAlloc` failure before writing through converted structures;
- makes ANSI write wrappers fail closed with `ERROR_NOT_ENOUGH_MEMORY` when
  conversion allocation fails;
- makes `CredReadA` fail closed if either the target-name conversion or returned
  credential conversion cannot allocate a valid output block.

## Acceptance Gate

Source-level gate:

- `docs/plan/check-srev-034.py` validates the schema and conversion cursor
  ownership.
- No `Cred_CREDENTIALW2A` cursor may start from `credW`.
- No attribute array cursor may advance by `sizeof(PCREDENTIAL_ATTRIBUTE*)`.

Windows runtime gate:

- In a sandboxed process, write/read/enumerate a `CredWriteA` generic
  credential with TargetName, Comment, TargetAlias, UserName, and at least one
  attribute keyword.
- Confirm `CredReadA` returns a single valid ANSI credential block and that the
  source wide credential remains unmodified during conversion.
