# SREV-022 Font Token Scoped Fallback Fix

## Decision

Use a compatibility design, not a blind reference-count patch:

```text
normal path gates -> scoped compatibility fallback -> owner-local restore -> evidence
```

The public Windows DDI does not provide a supported way for Sandboxie to rewrite
`ACCESS_STATE->SubjectSecurityContext` directly. Therefore the source-level fix
is to keep the unsupported rewrite as a scoped fallback only, add an explicit
mode switch, and give the minifilter and legacy parse-proc paths an owner-local
restore/dereference point.

## Owner And Gates

| Gate | Decision |
|---|---|
| Owner | Windows security/file-system path owns `ACCESS_STATE` and `SECURITY_SUBJECT_CONTEXT`; Sandboxie owns only the local compatibility fallback. |
| Legal path | Do not widen the subject-context rewrite. Preserve exact font/read/execute gates and add restore/dereference ownership. |
| Compatibility | Default to scoped fallback; allow `FontTokenMode=legacy` as escape hatch and `FontTokenMode=strict/off` to disable unsupported rewrite. |
| Minifilter topology | Pre-create stores a swap context in `CompletionContext`; post-create restores original fields and dereferences the token. |
| XP topology | Legacy parse-proc locally wraps the system parse call so restore/dereference happens after the continuation returns. |
| Evidence | Targeted SREV checker, core coverage, open-gate readback, whitespace check; Windows runtime remains required before claiming runtime proof. |

## Implementation Steps

1. Add `FILE_FONT_TOKEN_SWAP` state and `FontTokenMode` routing in `file.c`.
2. Change `File_ReplaceTokenIfFontRequest` to return a swap context for scoped fallback, keep legacy behavior for `FontTokenMode=legacy`, and disable for `strict/off`.
3. Add `File_RestoreTokenIfFontRequest` to restore `ClientToken`, `PrimaryToken`, and `ImpersonationLevel`, then `ObDereferenceObject`.
4. Register a minifilter post-create callback only for `IRP_MJ_CREATE`; pass the swap context through `CompletionContext`.
5. Wrap the XP parse-proc continuation with restore/dereference after the system parse proc returns.
6. Update SREV-022 spec, schema, checker, ledger, and coverage report from `runtime_design_open` to patched-source-needs-Windows-runtime-proof.
7. Run targeted verification and commit.

## Verification

Linux/source gate:

```bash
bash docs/plan/check-srev-022.sh
python3 docs/plan/check-core-coverage.py
bash docs/plan/check-open-runtime-gates.sh
git diff --check
```

Windows gate remains:

```text
repeated sandboxed GDI font opens show no token/pool growth and no Digital
Guardian-style crash regression across minifilter and XP parse-proc topologies.
```
