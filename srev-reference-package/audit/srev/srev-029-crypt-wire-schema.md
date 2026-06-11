# SREV-029: Crypt DPAPI Broker Wire Schema

## Finding

`Sandboxie/core/dll/crypt.c` packed caller `DATA_BLOB` fields and optional
description into `COM_CRYPT_PROTECT_DATA_REQ` using unchecked `ULONG` length
arithmetic. It then trusted the returned `COM_CRYPT_PROTECT_DATA_RPL` payload
lengths before copying data and description into `LocalAlloc` buffers.

`Sandboxie/core/svc/comserver2.cpp` parsed the same request using
`offset + length > req_len` style checks and built replies with unchecked
`rpl_len += ...` arithmetic.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata`
- `https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata`
- `https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/ns-wincrypt-crypt_integer_blob`
- `https://learn.microsoft.com/en-us/windows/desktop/api/WinBase/nf-winbase-localalloc`

Relevant contract:

- `CryptProtectData` and `CryptUnprotectData` use `DATA_BLOB` byte counts.
- Successful DPAPI output `pbData` is freed with `LocalFree`.
- `CryptUnprotectData` can return a description string, also freed with
  `LocalFree`.
- `LocalAlloc` takes a byte count; allocation/free ownership must match the
  API contract.

## Local Schema

Small machine-readable schema:

```text
docs/plan/srev-029-crypt-wire.schema.json
```

Request:

```text
MSG_HEADER
mode/flags/data_len/entropy_len/descr_len/prompt
data[data_len]
entropy[entropy_len]
descr[(descr_len + 1) WCHAR] when mode == P
```

Reply:

```text
MSG_HEADER
data_len/descr_len
data[data_len]
descr[(descr_len + 1) WCHAR] when returned by unprotect
```

## Source Change

DLL side:

- `Crypt_AddUlong` checks `ULONG` length addition before allocation.
- `Crypt_WcharsToBytesWithNull` checks `(chars + 1) * sizeof(WCHAR)`.
- `Crypt_GetBlobLength` rejects nonzero `cbData` with NULL `pbData`.
- `Crypt_ValidateReply` proves reply `h.length` covers the flexible payload
  before reading/copying reply fields.
- `pDataOut` and optional description buffers are allocated only after reply
  validation.

Service side:

- Request parsing uses `remaining = req_len - offset` before comparing segment
  lengths.
- Description length math includes the NUL terminator and is checked before
  writing `DataDescr[descr_len]`.
- Reply length is built with checked addition before copying `DataOut` and
  description payload back into the COM map buffer.

## Acceptance Gate

Source-level gate:

- `docs/plan/check-srev-029.py` validates the small JSON schema and the source
  patterns that enforce it.
- The old unchecked request/reply arithmetic and unchecked reply copies must not
  remain.

Windows runtime gate:

- Force DPAPI through the SbieSvc fallback path.
- Protect/unprotect normal data, empty data, entropy, empty description, and
  non-empty description.
- Exercise oversized `DATA_BLOB.cbData`, entropy, and description lengths near
  `ULONG_MAX` through a test harness and verify fail-closed behavior before any
  temp buffer copy.
