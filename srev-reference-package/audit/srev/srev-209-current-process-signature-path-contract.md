# SREV-209: Current Process Signature Path Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/drv/verify.h` was the top unnamed reviewable core file after
SREV-208. It declares the kernel certificate and signature verification
boundary: `SCertInfo`, `Verify_CertInfo`, `KphVerifyBuffer`, and
`KphVerifyCurrentProcess`.

The implementation in `Sandboxie/core/drv/verify.c` asks the kernel for the
current process image name with `SeLocateProcessImageName`, then builds the
sidecar signature path by appending `.sig`.

Before this fix, `KphVerifyCurrentProcess` treated the returned
`UNICODE_STRING.Buffer` as a null-terminated C string and used `wcscpy` /
`wcscat`. It also allocated `processFileName->MaximumLength + 4 * sizeof(WCHAR)`
bytes for the path buffer while setting `MaximumLength` to
`processFileName->MaximumLength + 5 * sizeof(WCHAR)`.

## Data

`verify.h`, `verify.c`, `KphVerifyCurrentProcess`, `SeLocateProcessImageName`,
`processFileName`, `signatureFileName`, `UNICODE_STRING.Length`,
`UNICODE_STRING.MaximumLength`, `UNICODE_STRING.Buffer`, `.sig`,
`KphReadSignature`, `KphVerifyFile`, and `ExFreePoolWithTag`.

## Official Shape

Microsoft documents `SeLocateProcessImageName` as returning an allocated buffer
that contains a `UNICODE_STRING` followed by the image-name string. The caller
must free that allocated buffer with the matching `ExFreeXxx` routine.

Microsoft documents `UNICODE_STRING.Length` as the byte length of the string,
not including a terminating NULL if one exists, and `MaximumLength` as the total
allocated byte size of the `Buffer`. Microsoft also documents that returned
`UNICODE_STRING` buffers might not be null-terminated.

Microsoft documents `RtlUnicodeStringCat` as the counted-string concatenation
shape for `UNICODE_STRING` buffers: it uses the destination buffer size to avoid
writing past the end and reports insufficient capacity. Sandboxie keeps this
path owner-local with explicit counted copy/append, but it must satisfy the
same shape: capacity is derived from byte lengths, the `.sig` suffix includes a
terminator in storage, and `Length` excludes that terminator.

References:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-selocateprocessimagename`
- `https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlunicodestringcat`

## Schema

`CURRENT_PROCESS_SIGNATURE_PATH_CONTRACT` says:

- `verify.h` owns the public driver verification declaration boundary.
- `verify.c` owns the current-process signature sidecar path builder.
- `SeLocateProcessImageName` output is a counted `UNICODE_STRING`, not a
  trusted null-terminated source string.
- The sidecar path allocation must reserve `processFileName->Length` bytes plus
  `.sig` plus one Unicode terminator.
- `signatureFileName->Length` excludes the terminator and
  `signatureFileName->MaximumLength` includes it.
- The implementation must not use `wcscpy` or `wcscat` on the returned process
  image buffer.

## Topology

```text
current EPROCESS
-> SeLocateProcessImageName
-> counted processFileName UNICODE_STRING
-> allocate UNICODE_STRING + Length + ".sig" + NUL
-> counted memcpy image bytes
-> counted memcpy ".sig\0"
-> KphReadSignature(signatureFileName)
-> KphVerifyFile(processFileName, signature)
```

## Logic Risk

The old path builder relied on two assumptions the official shape does not
prove: that the kernel-returned image path is null-terminated, and that
`MaximumLength` accurately represents enough storage for appending `.sig` plus
a terminator. If either assumption fails, the signature path builder can read or
write outside the legal counted string boundary before verification even
starts.

## Fix

`KphVerifyCurrentProcess` now rejects a missing image buffer or a path too long
to append `.sig`, derives the sidecar path capacity from
`processFileName->Length`, allocates exactly `UNICODE_STRING + image bytes +
".sig" + NUL`, sets `Length` and `MaximumLength` consistently, copies the image
path by byte count, and appends `.sig` including the terminator by byte count.

## Acceptance Gate

`docs/plan/check-srev-209.py` validates the draft-07 schema, official
references, `verify.h` declaration coordinates, source-level counted allocation
and copy/append shape in `verify.c`, removal of `wcscpy` / `wcscat` from the
current-process signature path builder, split ledger fragment, and preservation
of the `KphReadSignature` -> `KphVerifyFile` verification topology.
Runtime/build gate: Windows driver build plus signed-process verification smoke
where the process image path has normal and near-limit lengths, and malformed
or missing image-name state fails without reading past the counted
`UNICODE_STRING`.
