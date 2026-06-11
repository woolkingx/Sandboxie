# SREV-022: Font Token Subject Context Rewrite

## Stage Gate

| Field | Content |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input Artifact | `Sandboxie/core/drv/file.c` font access token rewrite |
| Output Artifact | Scoped fallback token-swap design with minifilter and XP restore/dereference paths |
| Owner | Driver file-open font compatibility path |
| Acceptance Gate | Source gate proves the unsupported subject-context rewrite is scoped, mode-gated, restored, and dereferenced by owner-local continuation paths; Windows runtime still proves font compatibility and token-reference ownership. |

## Official Shape

Microsoft `ObReferenceObject` documentation says the routine increments an
object reference count and the caller must decrement that reference with
`ObDereferenceObject` when done:

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobject
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obdereferenceobject
```

Microsoft `PsReferencePrimaryToken` documentation gives the token-specific
version of the same ownership rule: each successful token reference must be
matched by `ObDereferenceObject` or `PsDereferencePrimaryToken`:

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psreferenceprimarytoken
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psdereferenceprimarytoken
```

Microsoft `ACCESS_STATE` and `SECURITY_SUBJECT_CONTEXT` documentation adds a
stronger boundary rule: drivers must not directly modify `ACCESS_STATE`, and
must not directly modify or inspect `SECURITY_SUBJECT_CONTEXT` members to make
security decisions. The supported posture is to use security support routines:

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_access_state
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_security_subject_context
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-secapturesubjectcontext
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-sereleasesubjectcontext
```

## Local Shape

`File_ReplaceTokenIfFontRequest` handles a compatibility corner:

1. kernel-mode caller;
2. current process is sandboxed and has an original primary token saved in
   `proc->primary_token`;
3. requested access is limited to the specific read/execute font access mask;
4. path is under a Fonts directory or resolves as a boxed font path.

When those gates pass, the default `FontTokenMode=auto/scoped` path saves the
old subject-context token fields, references `proc->primary_token`, rewrites
`AccessState->SubjectSecurityContext.ClientToken`, raises the impersonation
level if needed, and marks callback data dirty. Minifilter create uses
`CompletionContext` to restore and dereference in post-create; the legacy XP
parse-proc path wraps the system parse continuation and restores after it
returns.

Compatibility modes:

```text
FontTokenMode=auto/scoped  scoped fallback with restore/dereference
FontTokenMode=legacy       old unscoped fallback for regression escape
FontTokenMode=strict/off   no unsupported subject-context rewrite
```

The source now names this as SREV-022 compatibility behavior: delayed
kernel-mode font opens from win32k may need the sandbox process's saved original
token substituted into the subject context. The implementation uses
`ClientToken` when possible, raises the impersonation level, and takes an extra
`ObReferenceObject(proc->primary_token)` only with a matching scoped
restore/dereference path unless `FontTokenMode=legacy` is explicitly selected.

## Finding

This was not a simple missing `ObDereferenceObject` beside the reference call.
The token pointer is handed to the I/O security path through an unsupported
direct `SECURITY_SUBJECT_CONTEXT` rewrite. A local dereference immediately after
assignment would risk turning the old resource leak into a token lifetime bug or
the previously observed crash class. The fix therefore binds the dereference to
the lower-path continuation point instead of the assignment site.

Later source-comment clarification: `file.c` now names SREV-022 both at the
compatibility path description and at the reference site. It no longer describes
the path as replacing `PrimaryToken` in `ACCESS_STATE`; the actual topology is a
direct, unsupported `SECURITY_SUBJECT_CONTEXT` rewrite that prefers
`ClientToken` and must not be rebalanced without Windows runtime proof. The old
generic third-party workaround and hack labels were removed from source, but the
runtime ownership proof remains in this spec and ledger.

## Required Strategy

Do not blind-patch the reference call. The safe route implemented here is:

1. keep normal traffic out of the rewrite with exact font/read/execute gates;
2. make the unsupported rewrite an explicit fallback mode;
3. store the original subject-context fields in `FILE_FONT_TOKEN_SWAP`;
4. restore and dereference at the owner-local continuation point:
   minifilter post-create or legacy XP parse-proc wrapper;
5. keep `FontTokenMode=legacy` as a regression escape hatch and
   `FontTokenMode=strict/off` for no unsupported rewrite;
6. require Windows runtime proof before claiming runtime closure.

## Runtime Capture Matrix

The Windows gate is not "font rendering still works". It must prove who owns
the substituted token reference after the unsupported subject-context rewrite.

Required dimensions:

- Windows builds: supported Windows 10 and Windows 11 releases, plus any XP /
  Server 2003 target used to keep `file_xp.c` alive.
- Path topology: minifilter `IRP_MJ_CREATE` path through `file_flt.c` and legacy
  XP parse-proc path through `file_xp.c`.
- Requestor shape: kernel-mode win32k delayed font open, user-mode file open
  negative control, active impersonation negative control, and non-sandboxed
  process negative control.
- Access mask: exact font read/execute mask, denied write/delete mask, and
  unrelated read path outside font compatibility.
- Path class: real `%SystemRoot%\Fonts` path, sandbox-boxed font path from the
  GDI helper, non-font path, missing file, and reparse/symlinked font path.
- Token state: `proc->primary_token` pointer, object reference delta before and
  after the create path, `ClientToken`/`PrimaryToken` field selected,
  `ImpersonationLevel`, and whether the downstream security/file-system path
  releases the substituted reference.
- Failure controls: `Process_Find` miss, missing `proc->primary_token`,
  `Obj_GetParseName` failure, boxed-path allocation failure, create failure,
  and Digital Guardian or equivalent callback-sensitive endpoint regression.
- Resource proof: repeated font opens with token reference count, paged pool,
  nonpaged pool, process lifetime, and driver unload readback.

## Fix

Source-level scoped compatibility fallback. `File_ReplaceTokenIfFontRequest`
now returns a `FILE_FONT_TOKEN_SWAP` context in scoped mode. The minifilter
`IRP_MJ_CREATE` operation registers a post callback and passes the swap context
through `CompletionContext`; `File_PostOperation` calls
`File_RestoreTokenIfFontRequest`. The XP parse-proc path wraps the system parse
continuation and restores immediately after it returns. `FontTokenMode=legacy`
keeps the old unscoped behavior, while `FontTokenMode=strict/off` disables the
unsupported rewrite.

## Runtime Gate

Required Windows proof:

1. sandboxed GDI font load succeeds before and after the change;
2. Digital Guardian or an equivalent callback-sensitive endpoint setup does not
   BSOD when the token path is exercised;
3. repeated font opens do not grow token object references or paged/nonpaged
   pool over time;
4. minifilter path and XP parse-proc path are verified independently because
   their continuation topology differs.
5. any future release/restore patch proves the exact owner of the substituted
   reference before calling `ObDereferenceObject` or changing
   `ClientToken`/`PrimaryToken` fields.

## Shared Runtime Capture Evidence

This SREV shares a kernel runtime evidence contract with SREV-027:

```text
docs/plan/srev-022-027-kernel-runtime-capture-playbook.md
docs/plan/srev-022-027-kernel-runtime-capture.schema.json
docs/plan/check-srev-022-027-kernel-runtime-capture.sh
```

The machine feature path for this entry is `font-token-subject-context`.

Windows gate: validate captured font-token records against
`docs/plan/srev-022-027-kernel-runtime-capture.schema.json` before any
release/restore or reference-balancing behavior change.
