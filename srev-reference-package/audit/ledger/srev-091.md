---
kind: srev-ledger-entry
id: SREV-091
title: Hook Trampoline PUSH/RET Stub Preservation
status: source-level-classified-after-official-intel-instruction-set-microsoft-executabl
owner: Sandboxie/core/dll/hook_tramp.c
spec: docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.md
schema: docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.schema.json
checker: docs/plan/check-srev-091.py
runtime_gate: not required for this comment-only clarification
---
### SREV-091: Hook Trampoline PUSH/RET Stub Preservation

| Field | Content |
|---|---|
| Severity | [major] |
| Status | source-level classified after official Intel instruction-set, Microsoft executable-code mutation, module unload, and driver unload shape; comment-only source clarification, no new runtime behavior |
| Evidence | `Sandboxie/core/dll/hook_tramp.c` emits detour bytes in `Hook_BuildJump`. Its 32-bit path has a special case for an existing `PUSH imm32`; `RET` stub used by Rising Antivirus. Intel's official manuals are the instruction-set source for `PUSH`, `RET`, and `JMP`; Microsoft documents executable-code mutation as needing page-protection/cache-coherency handling and documents module/driver unload as lifetime-sensitive. Before this SREV, the source comment described only the unload symptom. The code itself already preserved the correct owner shape by replacing only the immediate operand at `SourceAddr[1..4]` instead of rewriting the envelope to an E9 JMP. |
| Data | Writable alias address, executable address, existing 32-bit `PUSH imm32`; `RET` detour envelope, replacement target, ordinary 32-bit E9 fallback, 64-bit mov-rax/jmp-rax path, and caller-owned instruction-cache coherency gate. |
| Schema | `HOOK_TRAMP_PUSH_RET_STUB_PRESERVATION` says an existing 32-bit `PUSH imm32`; `RET` envelope is a third-party-owned detour shape; Sandboxie may replace only the PUSH immediate operand in that envelope; Sandboxie must not rewrite that envelope into a relative E9 JMP; ordinary non-PUSH/RET hooks keep the existing 32-bit E9 path; 64-bit hooks keep the mov-rax/jmp-rax path; code mutation and instruction-cache coherency remain owned by caller hook-install paths such as SREV-058. |
| Topology | `Hook_BuildJump` receives writable/executable code addresses, classifies existing instruction shape, preserves `PUSH imm32`; `RET` by operand-only replacement when present, otherwise uses the ordinary 32-bit E9 path or 64-bit mov-rax/jmp-rax path. The code-write boundary is separate from the caller-owned page-protection/cache-coherency boundary. |
| Logic Risk | Treating the special case as an arbitrary workaround invites a future cleanup to normalize it to E9. That would cross ownership boundaries: the third-party unload path owns and expects the original `PUSH`/`RET` envelope and restores only its immediate operand. |
| Official Shape | `docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.md` records Intel SDM plus Microsoft `VirtualProtect`, `FlushInstructionCache`, `FreeLibrary`, and `ZwUnloadDriver` references. `docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.schema.json` records the JSON Schema draft-07 local `HOOK_TRAMP_PUSH_RET_STUB_PRESERVATION` contract. |
| Fix | Comment-only source clarification: the Rising Antivirus branch now states the `PUSH`/`RET` envelope is preserved because the third-party unload path owns that shape and restores only the immediate operand. The executable bytes written by the branch are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-091.py` validates the draft-07 schema, official references, `PUSH imm32`; `RET` classifier, operand-only replacement, stale symptom-only comment removal, ordinary 32-bit E9 fallback preservation, 64-bit mov-rax/jmp-rax preservation, SREV-058 cache-coherency owner link, and ledger entry; `docs/plan/check-srev-091.sh` is the matrix wrapper. Runtime gate: not required for this comment-only clarification. Any future behavior change to this branch needs an x86 kernel/runtime matrix with a PUSH/RET-owning third-party detour and unload path, plus the existing instruction-cache gates. |
