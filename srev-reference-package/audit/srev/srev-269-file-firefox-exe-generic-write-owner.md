# SREV-269: File Firefox Exe Generic Write Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, Microsoft `NtCreateFile`, file access rights, and file-handle open documentation |
| Output artifact | `docs/plan/srev-269-file-firefox-exe-generic-write-owner.schema.json`, `docs/plan/check-srev-269.py`, `docs/plan/check-srev-269.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_NtCreateFileImpl` true-file fallback access narrowing for Firefox `.exe` probes |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

Inside `File_NtCreateFileImpl`, after Sandboxie has found the true file and is
about to decide whether an open can safely use the true path instead of the copy
path, Firefox-specific compatibility code strips `GENERIC_WRITE` when Firefox
opens an existing `.exe` outside the sandbox.

Before this SREV, the branch was labeled only as `$Workaround$ - 3rd party fix`.
The surrounding comments mention Firefox 106+ plugin executable probes, but the
source did not name the owner boundary: this is an access-mask narrowing step
before the true-file open decision, not permission to broaden write access.

## Official Shape

Microsoft documents `NtCreateFile.DesiredAccess` as the access mask requested
for the file object. For file objects, `GENERIC_WRITE` maps to a broad write
shape including `STANDARD_RIGHTS_WRITE`, `FILE_WRITE_DATA`,
`FILE_WRITE_ATTRIBUTES`, `FILE_WRITE_EA`, `FILE_APPEND_DATA`, and
`SYNCHRONIZE`.

Microsoft's file access rights documentation separately names the file-specific
rights, including data write, attribute write, EA write, append, delete, and
read attribute rights.

Microsoft's file-handle documentation says the caller must request access
rights that cover the operation it will perform; writing file data uses
`FILE_WRITE_DATA` or `GENERIC_WRITE`, and writing metadata uses
`FILE_WRITE_ATTRIBUTES` or `GENERIC_WRITE`.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile
https://learn.microsoft.com/windows/desktop/FileIO/file-access-rights-constants
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/opening-a-handle-to-a-file
```

## Data

`DesiredAccess`, `GENERIC_WRITE`, `FILE_DENIED_ACCESS`, `Dll_ImageType`,
`DLL_IMAGE_MOZILLA_FIREFOX`, `TruePath`, `.exe` extension check,
`CreateDisposition`, `FileType`, and the later `File_NtCreateTrueFile` call.

## Schema

`FILE_FIREFOX_EXE_GENERIC_WRITE_OWNER` says:

- `GENERIC_WRITE` is a broad file write-access mapping, not a narrow attribute
  probe;
- the compatibility narrowing is legal only inside the true-file fallback path
  where `FileType` exists and `CreateDisposition` is `FILE_OPEN` or
  `FILE_OPEN_IF`;
- the branch may strip `GENERIC_WRITE` only for `DLL_IMAGE_MOZILLA_FIREFOX`
  callers whose `TruePath` extension is exactly `.exe`;
- after the narrowing, the normal `(DesiredAccess & FILE_DENIED_ACCESS) == 0`
  gate still owns the decision to use `File_NtCreateTrueFile`;
- this SREV changes comments and proof only; Firefox/plugin compatibility still
  needs Windows runtime proof before behavior changes.

## Topology

```text
Firefox file open
  -> existing true-file fallback candidate
  -> TruePath .exe classification
  -> strip broad GENERIC_WRITE request
  -> existing FILE_DENIED_ACCESS gate
  -> true-file open or copy-path handling
```

## Logic Risk

The source is intentionally weakening a caller-requested access mask. That can
be a compatibility-preserving read route for an existing executable, but only if
the true-file gate stays narrow. If broadened beyond Firefox `.exe` probes, it
can hide real write intent and route too many opens to the true path. If removed
without a Windows Firefox/plugin matrix, plugin executable probing may regress.

## Fix

Comment-only source clarification. The source now names SREV-269 and states
that the branch strips only the broad `GENERIC_WRITE` mapping for Firefox 106+
plugin executable probes against existing true-path `.exe` files before the
normal true-file open decision. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-269.py` validates the draft-07 schema, official references,
source comment owner, Firefox image-type gate, `.exe` extension gate,
`GENERIC_WRITE` stripping, surrounding true-file fallback and
`FILE_DENIED_ACCESS` gates, removal of the anonymous `$Workaround$` label for
this branch, and the ledger fragment.

Runtime gate: Windows Firefox 106+ plugin executable smoke where the target
`.exe` exists outside the sandbox, Firefox's broad `GENERIC_WRITE` probe still
opens through the true-file path after narrowing, non-Firefox callers keep their
requested write access, and non-`.exe` paths do not receive this narrowing.
