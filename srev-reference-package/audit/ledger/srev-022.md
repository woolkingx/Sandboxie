---
kind: srev-ledger-entry
id: SREV-022
title: Font Token Subject Context Rewrite Has Unsupported Ownership Shape
status: patched-source-level-with-scoped-font-token-fallback-needs-windows-runtime-proof
owner: "Sandboxie/core/drv/file.c:1818-1903"
spec: docs/plan/srev-022-font-token-subject-context.md
schema: docs/plan/srev-022-font-token-subject-context.schema.json
checker: docs/plan/check-srev-022.sh
runtime_gate: repeated sandboxed GDI font opens show no token/pool growth and no Digital Guardian-style crash regression
---
### SREV-022: Font Token Subject Context Rewrite Has Unsupported Ownership Shape

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level scoped font-token fallback; needs Windows runtime proof |
| Evidence | `Sandboxie/core/drv/file.c:1818-1903` rewrites `AccessState->SubjectSecurityContext.ClientToken` to `proc->primary_token` only after exact delayed-font gates. The default scoped path records `FILE_FONT_TOKEN_SWAP`, takes `ObReferenceObject(proc->primary_token)`, passes the context through minifilter `CompletionContext` or the XP parse-proc wrapper, restores the original subject-context fields, and calls `ObDereferenceObject`. `FontTokenMode=legacy` keeps the old unscoped fallback as a regression escape hatch; `FontTokenMode=strict/off` disables the unsupported rewrite. |
| Data | Saved original process token pointer stored in `proc->primary_token`, inserted into an in-flight file-create `ACCESS_STATE` for kernel-mode font access. |
| Schema | Object/token references must be paired, but `ACCESS_STATE` and `SECURITY_SUBJECT_CONTEXT` members are reserved/support-routine-owned in the public DDI. The default scoped fallback must restore and dereference through owner-local continuation points; runtime capture must still prove font compatibility, no token/pool growth, and no callback-sensitive endpoint regression. |
| Topology | Minifilter pre-create mutates the I/O security context and passes `FILE_FONT_TOKEN_SWAP` to post-create through `CompletionContext`; legacy XP parse-proc wraps the system parse continuation and restores after it returns. |
| Logic Risk | Removing the reference beside assignment can turn a leak into token lifetime corruption or revive the earlier BSOD class; keeping the old unscoped behavior may leak token references on repeated font opens. The scoped fallback binds dereference to continuation ownership while preserving `legacy` escape. |
| Official Shape | `docs/plan/srev-022-font-token-subject-context.md` records Microsoft object reference ownership, token reference ownership, and the public no-direct-modification boundary for `ACCESS_STATE` / `SECURITY_SUBJECT_CONTEXT`. |
| Required Strategy | Treat this as a scoped compatibility fallback, not a local grep fix. Keep exact font gates, restore and dereference in minifilter/XP continuation owners, keep `legacy/strict/off` routing, and run Windows runtime proof before claiming runtime closure. |
| Runtime Capture Matrix | Supported Windows 10/11 plus XP/Server 2003 if `file_xp.c` remains supported; minifilter `IRP_MJ_CREATE` and legacy XP parse-proc topologies; kernel-mode win32k delayed font opens; user-mode, impersonation, and non-sandboxed negative controls; exact font read/execute mask and denied write/delete masks; real Fonts path, boxed font path, non-font path, missing file, and reparse/symlinked font path; `proc->primary_token`, reference deltas, `ClientToken`/`PrimaryToken` selection, `ImpersonationLevel`, downstream release observation, failure controls, repeated-open token reference count, paged/nonpaged pool, process lifetime, driver unload, and Digital Guardian or equivalent callback-sensitive endpoint regression. |
| Shared Runtime Capture Evidence | Runtime records use `docs/plan/srev-022-027-kernel-runtime-capture.schema.json` with feature path `font-token-subject-context`; `docs/plan/srev-022-027-kernel-runtime-capture-playbook.md` is the capture procedure; `docs/plan/check-srev-022-027-kernel-runtime-capture.sh` validates the shared kernel evidence contract. |
| Comment Contract | The source names SREV-022 as delayed kernel-mode font-open compatibility behavior, says the path substitutes the sandbox process's saved original token into the subject context only as a scoped fallback, and preserves `FontTokenMode=legacy` / `strict/off` routing. It no longer describes the active path as replacing `PrimaryToken` in `ACCESS_STATE`. The generic third-party workaround and hack labels were removed from source. |
| Acceptance Gate | `docs/plan/check-srev-022.sh` proves the unsupported token rewrite is scoped, mode-gated, restored, and dereferenced through owner-local continuation paths, and that the ledger keeps the concrete runtime capture matrix. Windows gate: repeated sandboxed GDI font opens show no token/pool growth and no Digital Guardian-style crash regression across minifilter and XP parse-proc topologies before runtime closure. |
