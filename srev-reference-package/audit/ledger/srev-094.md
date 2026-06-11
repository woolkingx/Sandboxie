---
kind: srev-ledger-entry
id: SREV-094
title: Ldr Inject Stack-Zero Owner
status: patched-source-level-after-official-x64-stack-ownership-x64-calling-convention-x
owner: Sandboxie/core/dll/util_32.asm
spec: docs/plan/srev-094-ldr-inject-stack-zero-owner.md
schema: docs/plan/srev-094-ldr-inject-stack-zero-owner.schema.json
checker: docs/plan/check-srev-094.py
runtime_gate: x86/x64 process-launch matrix with normal process entry, host injection, sandbox injection, F-Secure-compatible injected code, third-party entrypoint hooks, and crash/unwind observation
---
### SREV-094: Ldr Inject Stack-Zero Owner

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official x64 stack ownership, x64 calling convention, x64 prolog/epilog, x86 argument passing, stdcall, and custom/naked-entry shape; needs Windows x86/x64 injection runtime proof |
| Evidence | `Sandboxie/core/dll/util_32.asm` and `Sandboxie/core/dll/util_64.asm` clear `0x200` bytes of stack residue after `Ldr_Inject_Entry` because local comments say some injected F-Secure code assumes that stack area is zero. Microsoft documents x64 stack memory beyond the current `RSP` as volatile and says `RSP` must be set before reading or writing stack-frame values. Before this patch, both stubs restored the `Ldr_Inject_Entry` call frame and then wrote `[esp/rsp - 0x200, esp/rsp)` directly, so the compatibility write targeted a range the stub no longer owned. |
| Data | Patched image entrypoint, `Ldr_Inject_Entry32`, `Ldr_Inject_Entry64`, `Ldr_Inject_Entry`, restored original entrypoint bytes, former injection stack frame, F-Secure compatibility zeroing, x86 `ret` handoff, and x64 `jmp rdx` handoff. |
| Schema | `LDR_INJECT_STACK_ZERO_OWNER` says `Ldr_Inject_Entry` restores original entrypoint bytes and returns the original entrypoint address; the asm entry stub may clear the 0x200-byte former injection frame for F-Secure compatibility; the stack-zero operation must first allocate that 0x200-byte range by moving `ESP`/`RSP`; the stack-zero operation must restore `ESP`/`RSP` before returning or jumping to the original entrypoint; the x86 stub keeps the stdcall-style return path; the x64 stub keeps the existing jump-to-returned-entrypoint path; this SREV does not change patched entrypoint bytes or F-Secure compatibility policy. |
| Topology | x86 patched entrypoint calls `Ldr_Inject_Entry32`; the stub passes the return-address slot to `Ldr_Inject_Entry`, which restores original bytes and rewrites the return slot; the stub allocates and zeros a 0x200-byte stack range, restores `ESP`, and returns to the restored entrypoint. x64 patched entrypoint jumps to `Ldr_Inject_Entry64`; the stub calls `Ldr_Inject_Entry`, saves returned entrypoint in `RDX`, allocates and zeros a 0x200-byte stack range, restores `RSP`, and jumps to `RDX`. |
| Logic Risk | The compatibility policy may be necessary, but the previous implementation expressed it as a below-current-stack write. That is not a legal owner shape under the official x64 stack contract and is fragile around interrupts, debuggers, and future entrypoint-hook interactions. The minimal fix keeps the exact zeroing range but makes the stub own it while writing. |
| Official Shape | `docs/plan/srev-094-ldr-inject-stack-zero-owner.md` records Microsoft x64 stack usage, x64 calling convention, x64 prolog/epilog, x86 argument passing, `__stdcall`, naked/custom-entry, and naked-function rule references. `docs/plan/srev-094-ldr-inject-stack-zero-owner.schema.json` records the JSON Schema draft-07 local `LDR_INJECT_STACK_ZERO_OWNER` contract. |
| Fix | `Ldr_Inject_Entry32` now subtracts `0x200` from `ESP`, zeros from the new `ESP`, and restores `ESP` before `ret`. `Ldr_Inject_Entry64` now subtracts `0x200` from `RSP`, zeros from the new `RSP`, and restores `RSP` before `jmp rdx`. The zeroed byte range, entrypoint patch bytes, original-entrypoint restore path, and F-Secure compatibility policy are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-094.py` validates the draft-07 schema, official references, x86/x64 source shape, absence of below-stack `lea [esp/rsp-200h]` writes, stack restore before `ret` / `jmp rdx`, local `ldr_init.c` injection topology, and ledger entry; `docs/plan/check-srev-094.sh` is the matrix wrapper. Windows gate: x86/x64 process-launch matrix with normal process entry, host injection, sandbox injection, F-Secure-compatible injected code, third-party entrypoint hooks, and crash/unwind observation. |
